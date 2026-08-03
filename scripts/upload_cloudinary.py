import os
import glob
import json
import concurrent.futures
import cloudinary
import cloudinary.uploader

# Configuration
cloudinary.config(
    cloud_name="pmjavm9d",
    api_key="874176888116896",
    api_secret="Jey1HVA01lZ4WirRucao2DXFvWg"
)

IMAGES_DIR = "images"
OUTPUT_JSON = "offer_webapp/src/data/cloudinary_mapping.json"

def upload_image(filepath, current_map):
    filename = os.path.basename(filepath)
    # The key in mapping will just be the code e.g. "13-919-13-07"
    key = os.path.splitext(filename)[0]
    
    # Skip if already uploaded
    if key in current_map:
        return key, current_map[key]
        
    try:
        # Upload to a specific folder 'instruments' to keep cloudinary organized
        response = cloudinary.uploader.upload(
            filepath,
            folder="instruments",
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )
        # We only need to store the version and public_id, or just the secure_url
        # Let's store the public_id, so the frontend can use advanced transformations
        public_id = response.get('public_id')
        print(f"Uploaded: {filename} -> {public_id}")
        return key, public_id
    except Exception as e:
        print(f"Failed to upload {filename}: {e}")
        return key, None

def main():
    print("Starting Cloudinary Migration...")
    
    # Load existing mapping to resume if stopped
    mapping = {}
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            print(f"Loaded existing mapping with {len(mapping)} images. Resuming...")
            
    image_files = glob.glob(os.path.join(IMAGES_DIR, "*.png"))
    print(f"Found {len(image_files)} total images.")
    
    from tqdm import tqdm
    
    # Use ThreadPoolExecutor to upload concurrently
    # Max workers set to 10 to avoid hammering the API too hard
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        futures = {executor.submit(upload_image, filepath, mapping): filepath for filepath in image_files}
        
        # Use tqdm for a nice progress bar
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(image_files), desc="Uploading Images"):
            key, public_id = future.result()
            if public_id:
                mapping[key] = public_id
                
            # Save periodically (every 100 images)
            if len(mapping) % 100 == 0:
                os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
                with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(mapping, f, indent=4)
                    
    # Final save
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4)
        
    print("\nMigration Complete!")
    print(f"Total uploaded/mapped: {len(mapping)}")

if __name__ == "__main__":
    main()
