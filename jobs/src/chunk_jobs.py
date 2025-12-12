import json
import os
from openai import OpenAI
from common.storage import upload_json, download_text
from azure.storage.blob import BlobServiceClient

def get_cefr_guidelines(level):
    """Get vocabulary and grammar guidelines for CEFR levels"""
    guidelines = {
        "A1": "Use only present tense, very simple vocabulary (500-1000 words), short sentences (5-10 words), common everyday objects and actions.",
        "A2": "Use present and past tense, basic vocabulary (1000-2000 words), simple sentences (8-15 words), familiar topics and situations.",
        "B1": "Use various tenses, intermediate vocabulary (2000-3000 words), moderate complexity sentences, can include some idioms and expressions.",
        "B2": "Use all tenses including conditionals, advanced vocabulary (3000-4000 words), complex sentences, abstract concepts and nuanced language.",
        "C1": "Use sophisticated vocabulary (4000+ words), complex grammatical structures, idiomatic expressions, subtle meanings and implications."
    }
    return guidelines.get(level, guidelines["B1"])

def get_params_from_trigger():
    """Read story_id and chunk_id from trigger blob"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # List trigger blobs for chunk-job (check both manual and scheduled)
    container_client = blob_service.get_container_client("stories")
    blobs = list(container_client.list_blobs(name_starts_with="triggers/chunk-job-scheduled/"))
    if not blobs:
        blobs = list(container_client.list_blobs(name_starts_with="triggers/chunk-job/"))
    
    if not blobs:
        print("⏳ No trigger blobs found, waiting...")
        return None, None
    
    # Process the first trigger blob
    blob = blobs[0]
    blob_client = blob_service.get_blob_client(container="stories", blob=blob.name)
    trigger_data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
    story_id = trigger_data["story_id"]
    chunk_id = trigger_data["chunk_id"]
    
    # Delete the trigger blob after reading
    blob_client.delete_blob()
    print(f"✅ Read trigger blob: {blob.name}")
    print(f"   Story ID: {story_id}, Chunk ID: {chunk_id}")
    
    return story_id, chunk_id

def main():
    story_id, chunk_id = get_params_from_trigger()
    
    if not story_id or not chunk_id:
        print("No work to do, exiting...")
        return

    # Download manifest
    manifest_raw = download_text("stories", f"Users/{story_id}/manifest.json")
    manifest = json.loads(manifest_raw)
    
    # Get chapter info
    chapter = manifest["chapters"][chunk_id - 1]  # chunk_id is 1-indexed
    language = manifest["language"]
    level = manifest["readingLevel"]
    genre = manifest["genre"]
    
    # Initialize OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Generate chapter content
    system_prompt = f"""You are a language learning content creator. Write engaging stories in {language} 
    for {level} level learners. Follow CEFR {level} guidelines: {get_cefr_guidelines(level)}
    
    Write naturally and engagingly, but keep the language appropriate for the level."""
    
    user_prompt = f"""Write Chapter {chunk_id} of a {genre} story in {language} for {level} learners.
    
    Story Title: {manifest["title"]}
    Chapter Title: {chapter["title"]}
    Chapter Summary: {chapter["summary"]}
    
    Requirements:
    - Write 300-500 words in {language}
    - Use vocabulary and grammar appropriate for {level} level
    - Make it engaging and natural
    - Include dialogue if appropriate
    - End with a hook for the next chapter (unless it's chapter 10)
    
    Write ONLY the story content in {language}, no explanations or translations."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,
        max_tokens=1500
    )
    
    content = response.choices[0].message.content.strip()
    
    # Generate chunk
    chunk_content = {
        "storyId": story_id,
        "chunkId": chunk_id,
        "chapterTitle": chapter["title"],
        "content": content,
        "status": "completed",
        "wordCount": len(content.split())
    }

    # Upload chunk
    upload_json("stories", f"Users/{story_id}/chunks/chunk_{chunk_id}.json", chunk_content)
    print(f"✅ Chapter {chunk_id} generated for story {story_id}")
    print(f"   Title: {chapter['title']}")
    print(f"   Words: {chunk_content['wordCount']}")

if __name__ == "__main__":
    main()