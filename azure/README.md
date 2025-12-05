# Azure Deployment Guide

This guide walks you through deploying the Language Learning App to Azure Container Apps.

## Prerequisites

1. **Azure Account** with an active subscription
2. **Azure CLI** installed and configured
3. **Docker** installed locally
4. **Bash shell** (Linux/macOS or WSL on Windows)

## Quick Deploy

The easiest way to deploy is using the automated script:

```bash
cd azure
chmod +x deploy.sh
./deploy.sh
```

This script will set up everything automatically. See below for what it does and manual deployment steps.

## Architecture on Azure

```
┌─────────────────────────────────────────────────┐
│         Azure Container Apps Environment        │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   Auth   │  │   User   │  │   Book   │     │
│  │ Service  │  │ Service  │  │ Service  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │            │
│  ┌────┴─────────────┴─────────────┴─────┐     │
│  │       Translation Service             │     │
│  └───────────────┬──────────────────────┘     │
│                  │                             │
└──────────────────┼─────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼─────┐ ┌───▼────┐ ┌────▼────┐
│PostgreSQL │ │ Blob   │ │Container│
│ Database  │ │Storage │ │  Jobs   │
└───────────┘ └────────┘ └─────────┘
```

## Azure Resources Created

The deployment script creates the following resources:

1. **Resource Group** - Container for all resources
2. **Azure Container Registry (ACR)** - Stores Docker images
3. **Azure Database for PostgreSQL** - Managed database
4. **Azure Storage Account** - Blob storage for book content
5. **Azure Container Apps Environment** - Runtime environment
6. **4 Container Apps** - One for each microservice

## Manual Deployment Steps

If you prefer to deploy manually or need to customize:

### 1. Login to Azure

```bash
az login
az account set --subscription <your-subscription-id>
```

### 2. Set Variables

```bash
RESOURCE_GROUP="language-learning-rg"
LOCATION="eastus"
ACR_NAME="languagelearningacr"  # Must be globally unique
CONTAINERAPPS_ENV="language-learning-env"
DB_SERVER="language-learning-db"
STORAGE_ACCOUNT="languagelearningstore"  # Must be globally unique
```

### 3. Create Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### 4. Create Container Registry

```bash
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

az acr login --name $ACR_NAME
```

### 5. Build and Push Images

```bash
# From project root
cd services/auth-service
docker build -t $ACR_NAME.azurecr.io/auth-service:latest .
docker push $ACR_NAME.azurecr.io/auth-service:latest

# Repeat for other services
cd ../user-service
docker build -t $ACR_NAME.azurecr.io/user-service:latest .
docker push $ACR_NAME.azurecr.io/user-service:latest

cd ../book-service
docker build -t $ACR_NAME.azurecr.io/book-service:latest .
docker push $ACR_NAME.azurecr.io/book-service:latest

cd ../translation-service
docker build -t $ACR_NAME.azurecr.io/translation-service:latest .
docker push $ACR_NAME.azurecr.io/translation-service:latest
```

### 6. Create PostgreSQL Database

```bash
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --location $LOCATION \
  --admin-user dbadmin \
  --admin-password "ChangeThisPassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --storage-size 32 \
  --public-access 0.0.0.0

az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER \
  --database-name language_learning
```

### 7. Initialize Database Schema

```bash
# Get connection string
DB_CONNECTION="postgresql://dbadmin:ChangeThisPassword123!@$DB_SERVER.postgres.database.azure.com:5432/language_learning?sslmode=require"

# Run init script
psql "$DB_CONNECTION" -f ../database/init.sql
```

### 8. Create Storage Account

```bash
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Get connection string
STORAGE_CONNECTION=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --output tsv)

# Create containers
az storage container create \
  --name book-content \
  --connection-string "$STORAGE_CONNECTION"

az storage container create \
  --name book-covers \
  --connection-string "$STORAGE_CONNECTION"
```

### 9. Create Container Apps Environment

```bash
az containerapp env create \
  --name $CONTAINERAPPS_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

### 10. Deploy Services

```bash
# Auth Service
az containerapp create \
  --name auth-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image $ACR_NAME.azurecr.io/auth-service:latest \
  --target-port 8001 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DB_CONNECTION" \
    jwt-secret="your-super-secret-key" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    JWT_SECRET_KEY=secretref:jwt-secret

# User Service
az containerapp create \
  --name user-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image $ACR_NAME.azurecr.io/user-service:latest \
  --target-port 8002 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DB_CONNECTION" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AUTH_SERVICE_URL="http://auth-service"

# Book Service
az containerapp create \
  --name book-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image $ACR_NAME.azurecr.io/book-service:latest \
  --target-port 8003 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 1.0 \
  --memory 2Gi \
  --secrets \
    database-url="$DB_CONNECTION" \
    storage-connection="$STORAGE_CONNECTION" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AUTH_SERVICE_URL="http://auth-service" \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection \
    AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT"

# Translation Service
az containerapp create \
  --name translation-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image $ACR_NAME.azurecr.io/translation-service:latest \
  --target-port 8004 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DB_CONNECTION" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AUTH_SERVICE_URL="http://auth-service"
```

## Get Service URLs

```bash
# Get the URLs for external services
BOOK_URL=$(az containerapp show \
  --name book-service \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

TRANSLATION_URL=$(az containerapp show \
  --name translation-service \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Book Service: https://$BOOK_URL"
echo "Translation Service: https://$TRANSLATION_URL"
```

## Update Frontend Configuration

Update your frontend to use the Azure URLs:

```typescript
// frontend/src/config.ts
export const API_BASE_URLS = {
  book: 'https://book-service.xxxxx.eastus.azurecontainerapps.io',
  translation: 'https://translation-service.xxxxx.eastus.azurecontainerapps.io'
};
```

## Monitoring & Logs

### View Logs

```bash
# View logs for a specific service
az containerapp logs show \
  --name auth-service \
  --resource-group $RESOURCE_GROUP \
  --follow

# View logs for all services
az monitor activity-log list \
  --resource-group $RESOURCE_GROUP
```

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app language-learning-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app language-learning-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey -o tsv)

# Update container apps with instrumentation key
az containerapp update \
  --name auth-service \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=$INSTRUMENTATION_KEY"
```

## Scaling

### Manual Scaling

```bash
# Scale a specific service
az containerapp update \
  --name book-service \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 10
```

### Auto-scaling Rules

```bash
# Add CPU-based scaling
az containerapp update \
  --name book-service \
  --resource-group $RESOURCE_GROUP \
  --scale-rule-name cpu-scale \
  --scale-rule-type cpu \
  --scale-rule-metadata "type=Utilization" "value=70"
```

## Cost Optimization

1. **Use Consumption Plan**: Pay only for what you use
2. **Set min replicas to 0**: For non-prod environments
3. **Use smaller SKUs**: Start with Basic tier
4. **Monitor usage**: Use Azure Cost Management
5. **Set budgets**: Get alerts before overspending

### Estimated Monthly Costs (Consumption Plan)

- Container Apps: ~$20-50/month (depending on traffic)
- PostgreSQL (Burstable): ~$15-30/month
- Storage (LRS): ~$5-10/month
- Container Registry (Basic): ~$5/month
- **Total**: ~$45-95/month for development

## Security Best Practices

1. **Use Azure Key Vault** for secrets
2. **Enable Private Endpoints** for database
3. **Configure CORS** properly
4. **Use Managed Identity** for Azure services
5. **Enable SSL/TLS** for all connections
6. **Implement Rate Limiting**
7. **Use Azure AD** for authentication (optional)

## CI/CD with GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Build and Deploy
        run: |
          cd azure
          ./deploy.sh
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
az containerapp logs show --name [service-name] --resource-group $RESOURCE_GROUP

# Check revision status
az containerapp revision list --name [service-name] --resource-group $RESOURCE_GROUP
```

### Database Connection Issues

```bash
# Test connection
psql "$DB_CONNECTION" -c "SELECT 1"

# Check firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER
```

### Image Pull Errors

```bash
# Check ACR credentials
az acr credential show --name $ACR_NAME

# Login and push again
az acr login --name $ACR_NAME
docker push $ACR_NAME.azurecr.io/[service-name]:latest
```

## Clean Up

To delete all resources:

```bash
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

## Next Steps

1. **Set up Custom Domain** - Use your own domain name
2. **Configure SSL Certificates** - Let's Encrypt or Azure-managed
3. **Add CDN** - Azure Front Door for better performance
4. **Implement Backup** - Database backups and disaster recovery
5. **Set up Monitoring** - Application Insights and alerts
6. **Load Testing** - Test with Azure Load Testing

## Support

For issues with Azure deployment:
- Check [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- Review [Azure PostgreSQL Documentation](https://learn.microsoft.com/en-us/azure/postgresql/)
- Open an issue on GitHub

