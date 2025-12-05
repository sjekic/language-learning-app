#!/bin/bash
# Azure Container Apps Deployment Script
# This script builds and deploys all microservices to Azure Container Apps

set -e  # Exit on error

# Configuration - UPDATE THESE VALUES
RESOURCE_GROUP="language-learning-rg"
LOCATION="eastus"
ACR_NAME="languagelearningacr"  # Must be globally unique
CONTAINERAPPS_ENVIRONMENT="language-learning-env"
DATABASE_SERVER="language-learning-db"
STORAGE_ACCOUNT="languagelearningstore"  # Must be globally unique

echo "🚀 Starting deployment to Azure Container Apps..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "ACR: $ACR_NAME"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Login to Azure (if not already logged in)
echo -e "${BLUE}📝 Checking Azure login...${NC}"
az account show > /dev/null 2>&1 || az login

# Step 2: Create Resource Group
echo -e "${BLUE}📦 Creating resource group...${NC}"
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION \
  --output table

# Step 3: Create Azure Container Registry
echo -e "${BLUE}🏗️  Creating Azure Container Registry...${NC}"
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true \
  --output table

# Step 4: Login to ACR
echo -e "${BLUE}🔐 Logging in to ACR...${NC}"
az acr login --name $ACR_NAME

# Step 5: Create PostgreSQL Database
echo -e "${BLUE}🗄️  Creating PostgreSQL Database...${NC}"
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DATABASE_SERVER \
  --location $LOCATION \
  --admin-user dbadmin \
  --admin-password "ChangeThisPassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --storage-size 32 \
  --public-access 0.0.0.0 \
  --output table

# Create database
echo -e "${BLUE}📊 Creating database...${NC}"
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DATABASE_SERVER \
  --database-name language_learning \
  --output table

# Step 6: Create Azure Storage Account
echo -e "${BLUE}💾 Creating Storage Account...${NC}"
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --output table

# Create blob containers
echo -e "${BLUE}📂 Creating blob containers...${NC}"
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --output tsv)

az storage container create \
  --name book-content \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --output table

az storage container create \
  --name book-covers \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --output table

# Step 7: Create Container Apps Environment
echo -e "${BLUE}🌐 Creating Container Apps Environment...${NC}"
az containerapp env create \
  --name $CONTAINERAPPS_ENVIRONMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --output table

# Step 8: Build and Push Docker Images
echo -e "${BLUE}🐳 Building and pushing Docker images...${NC}"

SERVICES=("auth-service" "user-service" "book-service" "translation-service")

for SERVICE in "${SERVICES[@]}"; do
  echo -e "${GREEN}Building $SERVICE...${NC}"
  
  cd ../services/$SERVICE
  
  docker build -t $ACR_NAME.azurecr.io/$SERVICE:latest .
  docker push $ACR_NAME.azurecr.io/$SERVICE:latest
  
  cd ../../azure
  
  echo -e "${GREEN}✅ $SERVICE built and pushed${NC}"
done

# Step 9: Get connection strings
DATABASE_CONNECTION_STRING="postgresql://dbadmin:ChangeThisPassword123!@$DATABASE_SERVER.postgres.database.azure.com:5432/language_learning?sslmode=require"

# Step 10: Deploy Container Apps
echo -e "${BLUE}🚢 Deploying Container Apps...${NC}"

# Auth Service
echo -e "${GREEN}Deploying auth-service...${NC}"
az containerapp create \
  --name auth-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENVIRONMENT \
  --image $ACR_NAME.azurecr.io/auth-service:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --target-port 8001 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DATABASE_CONNECTION_STRING" \
    jwt-secret="your-super-secret-jwt-key-change-this" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    JWT_SECRET_KEY=secretref:jwt-secret \
  --output table

# User Service
echo -e "${GREEN}Deploying user-service...${NC}"
az containerapp create \
  --name user-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENVIRONMENT \
  --image $ACR_NAME.azurecr.io/user-service:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --target-port 8002 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DATABASE_CONNECTION_STRING" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AUTH_SERVICE_URL="http://auth-service" \
  --output table

# Book Service
echo -e "${GREEN}Deploying book-service...${NC}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az containerapp create \
  --name book-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENVIRONMENT \
  --image $ACR_NAME.azurecr.io/book-service:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --target-port 8003 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 1.0 \
  --memory 2Gi \
  --secrets \
    database-url="$DATABASE_CONNECTION_STRING" \
    storage-connection="$STORAGE_CONNECTION_STRING" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AUTH_SERVICE_URL="http://auth-service" \
    AZURE_SUBSCRIPTION_ID="$SUBSCRIPTION_ID" \
    AZURE_RESOURCE_GROUP="$RESOURCE_GROUP" \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection \
    AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
    AZURE_STORAGE_CONTAINER_NAME="book-content" \
    AZURE_STORAGE_COVER_CONTAINER="book-covers" \
  --output table

# Translation Service
echo -e "${GREEN}Deploying translation-service...${NC}"
az containerapp create \
  --name translation-service \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENVIRONMENT \
  --image $ACR_NAME.azurecr.io/translation-service:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --target-port 8004 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DATABASE_CONNECTION_STRING" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AUTH_SERVICE_URL="http://auth-service" \
    LINGUEE_API_URL="https://linguee-api.fly.dev/api/v2/translations" \
  --output table

# Step 11: Initialize Database
echo -e "${BLUE}🗄️  Initializing database schema...${NC}"
# You may need to run the init.sql manually or use a migration tool
echo "To initialize the database, run:"
echo "psql \"$DATABASE_CONNECTION_STRING\" -f ../database/init.sql"

# Step 12: Get service URLs
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo "Service URLs:"
echo "============================================"

AUTH_URL=$(az containerapp show --name auth-service --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
USER_URL=$(az containerapp show --name user-service --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
BOOK_URL=$(az containerapp show --name book-service --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
TRANSLATION_URL=$(az containerapp show --name translation-service --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)

echo "Auth Service: https://$AUTH_URL"
echo "User Service: https://$USER_URL"
echo "Book Service: https://$BOOK_URL"
echo "Translation Service: https://$TRANSLATION_URL"
echo ""
echo "Update your frontend to use these URLs!"

