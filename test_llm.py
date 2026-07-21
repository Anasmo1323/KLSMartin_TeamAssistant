from llama_cpp import Llama
import time

print("Loading model...")
start = time.time()
llm = Llama(
    model_path="models/qwen2-7b-instruct-q4_k_m.gguf",
    n_gpu_layers=-1,
    n_ctx=512,
    verbose=False
)
print(f"Model loaded in {time.time() - start:.2f} seconds.")

system_msg = "You are a medical data assistant. Extract ONLY the base family name of the surgical instrument from the description, ignoring physical variations (like size, mm, cm, straight, curved, fine, blunt, ratchet, teeth). Output strictly the family name and nothing else."

test_descs = [
    "TC gold dissecting scissors, acc. to Metzenbaum-Fino, fine, straight, length 14.5 cm",
    "Operating scissors, blunt/blunt, straight, length 13 cm",
    "Brain knive, acc. to Virchow, with hollow handle, cutting length 200 mm, length 33.5 cm",
    "Forceps, Adson, 1x2 teeth, 12cm"
]

for desc in test_descs:
    print(f"\nDesc: {desc}")
    t0 = time.time()
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": desc}
        ],
        temperature=0.0,
        max_tokens=30
    )
    result = response['choices'][0]['message']['content']
    print(f"Family: {result}")
    print(f"Time: {time.time() - t0:.2f} seconds")
