import json
import os
from openai import OpenAI
from common.storage import upload_json, download_text, download_json_if_exists
from common.contracts import validate_chunk, validate_manifest, validate_trigger
from common.triggers import check_claim

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

def main(trigger=None):
    if trigger is None:
        from chunk_poller import main as poll
        return poll()
    validate_trigger(trigger, "chunk-job")
    story_id = trigger["story_id"]
    chapter_start = trigger.get("chapter_start", trigger.get("chunk_id"))
    chapter_end = trigger.get("chapter_end", trigger.get("chunk_id"))
    batch_id = trigger.get("batch_id", trigger.get("chunk_id"))

    # Download manifest
    manifest_raw = download_text("stories", f"Users/{story_id}/manifest.json")
    manifest = json.loads(manifest_raw)
    
    chapters = validate_manifest(manifest, story_id)
    if chapter_end > len(chapters):
        raise ValueError("Requested chapter range exceeds manifest")
    language = manifest["language"]
    level = manifest["readingLevel"]
    genre = manifest["genre"]
    
    # Initialize OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print(f"Generating chapters {chapter_start} to {chapter_end} for story {story_id}...")
    
    # Generate each chapter in the batch
    for chunk_id in range(chapter_start, chapter_end + 1):
        chapter = chapters[chunk_id - 1]
        path = f"Users/{story_id}/chunks/chunk_{chunk_id}.json"
        try:
            existing = download_json_if_exists("stories", path)
            validate_chunk(existing, story_id, chunk_id)
        except ValueError:
            pass  # A missing/corrupt output can be regenerated on retry.
        else:
            continue
        
        # Generate chapter content
        system_prompt = f"""You are a language learning content creator. Write engaging stories in {language} 
        for {level} level learners. Follow CEFR {level} guidelines: {get_cefr_guidelines(level)}
        
        Format your output with markdown:
        - Use **Title** for chapter titles
        - Use double line breaks between paragraphs
        - Write naturally and engagingly"""
        
        user_prompt = f"""Write Chapter {chunk_id} of a {genre} story in {language} for {level} learners.
        
        Story Title: {manifest["title"]}
        Chapter Title: {chapter["title"]}
        Chapter Summary: {chapter["summary"]}
        
        Requirements:
        - Start with: **{chapter["title"]}**
        - Write 300-500 words in {language}
        - Use vocabulary and grammar appropriate for {level} level
        - Separate paragraphs with double line breaks
        - Make it engaging and natural
        - Include dialogue if appropriate
        - End with a hook for the next chapter (unless it's chapter 10)
        
        Write ONLY the story content in {language}, no explanations or translations."""
        
        check_claim()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Chapter {chunk_id} generation returned empty content")
        content = content.strip()
        
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
        validate_chunk(chunk_content, story_id, chunk_id)
        upload_json("stories", path, chunk_content)
        print(f"Chapter {chunk_id} generated ({chunk_content['wordCount']} words)")
    
    print(f"Batch {batch_id} complete: chapters {chapter_start}-{chapter_end}")

if __name__ == "__main__":
    main()
