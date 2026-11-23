import type { AiMessage } from "../types";
import { img } from "../ui";

const m = (id: string, role: "user" | "assistant", text: string, imageUrl?: string, status?: string): AiMessage =>
  ({ id, role, text, imageUrl, status });

export const suggestionChips = [
  "Generate a Dubai beach image",
  "Flights Dubai to London next Friday",
  "Weather in London",
  "Summarise my emails",
  "Make a promo video for Mirsal",
];

export const aiContacts = [
  { id: "dubai-beach-photo", name: "Dubai beach photo for Instagram", group: "Today" },
  { id: "videos", name: "Videos", group: "Today" },
  { id: "flights-dxb-lhr", name: "Flights DXB → LHR in December", group: "Today" },
  { id: "arabic-nlp", name: "Arabic NLP models comparison", group: "Yesterday" },
  { id: "abu-dhabi-weekend", name: "Weekend plan in Abu Dhabi", group: "Yesterday" },
  { id: "rag-vs-fine-tuning", name: "Explain RAG vs fine-tuning", group: "Previous 7 days" },
  { id: "kyoto-blossoms", name: "Kyoto cherry blossom image", group: "Previous 7 days" },
  { id: "cover-letter-ai", name: "Cover letter for AI engineer role", group: "Previous 7 days" },
  { id: "meal-prep", name: "Healthy meal prep for the week", group: "Previous 7 days" },
  { id: "python-photo-rename", name: "Python script to rename photos", group: "Previous 7 days" },
  { id: "golden-visa", name: "UAE Golden Visa requirements", group: "Previous 7 days" },
  { id: "mom-birthday-gift", name: "Gift ideas for Mom's birthday", group: "Previous 30 days" },
  { id: "langgraph-learning", name: "Learning plan for LangGraph", group: "Previous 30 days" },
  { id: "london-weather", name: "Weather in London next week", group: "Previous 30 days" },
  { id: "resume-feedback", name: "Resume feedback for ML roles", group: "Previous 30 days" },
];

const threads: Record<string, AiMessage[]> = {
  "dubai-beach-photo": [
    m("u1", "user", "Generate a beautiful photo of a Dubai beach at sunset for my Instagram"),
    m("a1", "assistant",
      "Here's your generated image — a stunning Dubai beach at golden hour 🌅",
      img("photo-1512453979798-5ea266f8880c", 1200),
      "Reasoned for 4s"),
    m("u2", "user", "Can you also make a version with a more vibrant color grade?"),
    m("a2", "assistant",
      "Sure — generating a second version with enhanced saturation and warmer tones.",
      img("photo-1507525428034-b723cf961d3e", 1200),
      "Reasoned for 5s"),
    m("u3", "user", "Perfect! Can you write an Instagram caption for the first one?"),
    m("a3", "assistant",
      "Here are a few options:\n\n**Option 1:**\n*Golden hours hit different in Dubai 🌊✨*\n\n**Option 2:**\n*Where the sky meets the sea — JBR after sunset 🔥*\n\n**Option 3:**\n*Dubai nights and beach vibes. No filter needed.*", undefined, "Reasoned for 2s"),
  ],

  "flights-dxb-lhr": [
    m("u1", "user", "Find flights from Dubai to London next Friday"),
    m("a1", "assistant",
      "I found several flights from Dubai (DXB) to London (LHR) on **Friday, Dec 12**:\n\n" +
      "1. **Emirates EK 007** — Depart 01:45, arrive 07:10 · 7h 25m · Non-stop · From AED 3,250\n" +
      "2. **British Airways BA 107** — Depart 14:30, arrive 20:00 · 7h 30m · Non-stop · From AED 2,890\n" +
      "3. **flydubai FZ 601** — Depart 08:00, arrive 13:30 · 7h 30m · Non-stop · From AED 1,950\n" +
      "4. **Qatar QR 101** — Depart 22:00, arrive 06:30+1 · 8h 30m · 1 stop · From AED 2,100\n\n" +
      "The cheapest option is **flydubai at AED 1,950**. Want me to add any to your calendar?", undefined, "Searched 12 flights · 3s"),
    m("u2", "user", "Add the Emirates one to my calendar please"),
    m("a2", "assistant",
      "Done! Added to your calendar:\n\n**📅 Emirates EK 007**\n" +
      "- Date: Fri, Dec 12\n" +
      "- Time: 01:45 → 07:10 (7h 25m)\n" +
      "- Route: Dubai (DXB) → London Heathrow (LHR)\n" +
      "- Price: AED 3,250\n\n" +
      "You'll find it under the **Flights** calendar. Want me to search return flights too?", undefined, "Added to calendar · 1s"),
    m("u3", "user", "Yes, same date returning Monday"),
    m("a3", "assistant",
      "Found return flights for **Monday, Dec 15**:\n\n" +
      "1. **Emirates EK 006** — Depart 09:00, arrive 17:30 · 8h 30m · Non-stop · From AED 2,900\n" +
      "2. **BA 108** — Depart 15:30, arrive 00:30+1 · 7h 30m · Non-stop · From AED 2,650\n\n" +
      "Adding both Emirates flights to your calendar would save you about AED 400 compared to booking separately. Want me to do that?", undefined, "Searched 8 return flights · 2s"),
  ],

  "arabic-nlp": [
    m("u1", "user", "Compare the top Arabic NLP models available in 2024"),
    m("a1", "assistant",
      "Here's a comparison of the leading Arabic NLP models:\n\n**1. Jais (30B)** by Technology Innovation Institute\n" +
      "- Open-weight, trained on 129GB Arabic text\n" +
      "- Best for: general-purpose Arabic generation\n" +
      "- Available on HuggingFace under Apache 2.0\n\n" +
      "**2. CAMeL-LM (7B & 3B)** by Qatari Computing Research Institute\n" +
      "- Fine-tuned from LLaMA, strong on Arabic instruction following\n" +
      "- Supports code-switching (Arabic + English)\n\n" +
      "**3. AraBERTv0.2** by MBZUAI\n" +
      "- Lighter model, good for classification tasks\n" +
      "- Based on BERT architecture\n\n" +
      "| Model | Params | License | Strength |\n|---|---|---|---|\n| Jais 30B | 30B | Apache 2.0 | General generation |\n| CAMeL-LM 7B | 7B | MIT | Instruction tuning |\n| AraBERT | 110M | CC-BY-SA | Classification |\n\n" +
      "For production use in the UAE, **Jais** is the strongest choice. For lighter deployments, **CAMeL-LM 3B** is very efficient.", undefined, "Searched 8 sources · 12s"),
    m("u2", "user", "How do I fine-tune Jais on my own Arabic dataset?"),
    m("a2", "assistant",
      "Here's a practical fine-tuning pipeline for Jais:\n\n```python\n" +
      "from transformers import AutoModelForCausalLM, AutoTokenizer\n" +
      "from peft import LoraConfig, get_peft_model\n" +
      "\n" +
      "model_name = \"ibtissame/jais-30b-chat-hf\"\n" +
      "tokenizer = AutoTokenizer.from_pretrained(model_name)\n" +
      "model = AutoModelForCausalLM.from_pretrained(\n" +
      "    model_name,\n" +
      "    torch_dtype=torch.bfloat16,\n" +
      "    device_map=\"auto\"\n" +
      ")\n" +
      "\n" +
      "config = LoraConfig(\n" +
      "    r=16,\n" +
      "    lora_alpha=32,\n" +
      "    target_modules=[\"q_proj\", \"k_proj\", \"v_proj\"],\n" +
      "    lora_dropout=0.05,\n" +
      "    bias=\"none\",\n" +
      ")\n" +
      "model = get_peft_model(model, config)\n" +
      "```\n\n" +
      "Key tips:\n" +
      "- Use **LoRA** to keep GPU memory under control (~40GB for 30B)\n" +
      "- Set `sequence_length=2048` for most Arabic tasks\n" +
      "- Train on **Madaix** or **ArabicCorpus** for pre-training data\n" +
      "- Use **DeepSpeed ZeRO-3** if you have multi-GPU setup\n\n" +
      "Want me to generate a full training script for your specific dataset?", undefined, "Reasoned for 8s"),
  ],

  "abu-dhabi-weekend": [
    m("u1", "user", "Plan a weekend itinerary in Abu Dhabi for a family of four"),
    m("a1", "assistant",
      "Here's a family-friendly weekend itinerary for Abu Dhabi:\n\n**Day 1 — Culture & Icons**\n\n**Morning (9 AM – 1 PM)**\n" +
      "- Visit **Grand Mosque** (free entry, dress code provided)\n" +
      "- Breakfast at **Al Nafoorah** inside Emirates Palace\n\n" +
      "**Afternoon (2 PM – 5 PM)**\n" +
      "- Drive through **Corniche Road** — the kids will love the beach stop\n" +
      "- Visit **Qasr Al Watan** (Presidential Palace) — interactive exhibits for children\n\n" +
      "**Evening (6 PM – 9 PM)**\n" +
      "- Dinner at **Nedum** (modern Emirati, Corniche views)\n" +
      "- Night walk at **Yas Marina Circuit** — the lights are stunning\n\n" +
      "**Day 2 — Adventure & Relax**\n\n**Morning**\n" +
      "- **Ferrari World** or **Warner Bros. Theme Park** (Yas Island)\n\n" +
      "**Afternoon**\n" +
      "- Lunch at **Abu Dhabi Mall food court**\n" +
      "- Relax at **Saadiyat Beach** — calm waters great for kids\n\n" +
      "Estimated cost: ~AED 1,200–1,800 for the family (excluding hotel).", undefined, "Reasoned for 6s"),
    m("u2", "user", "Can you add some restaurant recommendations near the Corniche?"),
    m("a2", "assistant",
      "Here are great family spots near the Corniche:\n\n**For lunch:**\n" +
      "- **Sheikh Rostadero** — famous Emirati grilled meats, very casual\n" +
      "- **Aseel** — Lebanese cuisine, kids menu available\n" +
      "- **The Burger Lab** — solid burgers, quick service\n\n" +
      "**For dinner:**\n" +
      "- **Nedum** — modern Emirati, beautiful Corniche views\n" +
      "- **Taverna** — Italian, right on the corniche promenade\n\n" +
      "All within a 5-minute drive from the main Corniche area.", undefined, "Searched 6 restaurants · 4s"),
    m("u3", "user", "Yes, add the dinner reservations for Friday 8 PM"),
    m("a3", "assistant",
      "I've added the reminder:\n\n**Friday, 8:00 PM**\n" +
      "- 🍽️ Dinner at **Nedum** — Corniche, Abu Dhabi\n" +
      "- 👨‍👩‍👧‍👦 Party of 4\n\n" +
      "You can modify or cancel this anytime from your Calendar app.", undefined, "Added reminder · 1s"),
  ],

  "rag-vs-fine-tuning": [
    m("u1", "user", "Explain RAG vs fine-tuning for building a company knowledge base"),
    m("a1", "assistant",
      "Great question — here's when to use each approach:\n\n**RAG (Retrieval-Augmented Generation)**\n" +
      "- Retrieves relevant documents **at query time**\n" +
      "- Knowledge stays **up-to-date automatically**\n" +
      "- Works well when docs change frequently\n" +
      "- Lower compute cost per inference\n" +
      "- You can cite sources explicitly\n\n" +
      "```python\n" +
      "# Minimal RAG pipeline\n" +
      "docs = vector_db.similarity_search(query, k=5)\n" +
      "context = \"\\n\".join(d.text for d in docs)\n" +
      "response = llm.generate(f\"Context: {context}\\nQuestion: {query}\")\n" +
      "```\n\n" +
      "**Fine-Tuning**\n" +
      "- **Bakes knowledge into model weights**\n" +
      "- Faster inference (no retrieval step)\n" +
      "- Better for style/tone adaptation\n" +
      "- Need retraining when knowledge changes\n\n" +
      "**Recommendation**\n" +
      "For a company KB: **start with RAG**. It's cheaper to set up, keeps info current, and gives you traceability. Fine-tune only if you need the model to adopt a specific communication style across all outputs.\n\n" +
      "Want a detailed RAG implementation guide for your tech stack?", undefined, "Reasoned for 5s"),
    m("u2", "user", "Yes — we're using Python and Azure"),
    m("a2", "assistant",
      "Here's a production-ready RAG architecture for Azure:\n\n**Stack**\n" +
      "- **Embeddings:** Azure OpenAI `text-embedding-ada-002`\n" +
      "- **Vector store:** Azure AI Search (Managed Vector Index)\n" +
      "- **Orchestration:** LangChain + Azure Container Apps\n" +
      "- **LLM:** Azure OpenAI `gpt-4-turbo`\n\n" +
      "```python\n" +
      "from langchain_community.vectorstores import AzureSearch\n" +
      "from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI\n" +
      "\n" +
      "embeddings = AzureOpenAIEmbeddings(\n" +
      "    deployment=\"text-embedding-ada-002\",\n" +
      "    chunk_size=500,\n" +
      "    chunk_overlap=50\n" +
      ")\n" +
      "store = AzureSearch(embeddings=embeddings)\n" +
      "llm = AzureChatOpenAI(deployment_name=\"gpt-4-turbo\", temperature=0)\n" +
      "```\n\n" +
      "**Cost estimate**\n" +
      "- Embedding 10K docs: ~$2/month\n" +
      "- 1,000 queries/day: ~$15/month\n" +
      "- Total: **under $20/month** for small-scale deployment\n\n" +
      "Want me to generate the full deployment YAML for Azure Container Apps?", undefined, "Reasoned for 7s"),
  ],

  "kyoto-blossoms": [
    m("u1", "user", "Generate an image of cherry blossoms in Kyoto during spring"),
    m("a1", "assistant",
      "Here's your generated image — the Philosopher's Path in full bloom 🌸",
      img("photo-1556909114-f6e7ad7d3136", 1200)),
    m("u2", "user", "Beautiful! What's the best time of year to visit Kyoto for hanami?"),
    m("a2", "assistant",
      "**Peak bloom in Kyoto** typically falls between late March and mid-April:\n\n" +
      "- **Early March:** Some early bloomers at Heian Shrine\n" +
      "- **Late March – Early April:** Peak season at Philosopher's Path & Maruyama Park\n" +
      "- **Mid-April:** Late bloomers at Arashiyama area\n\n" +
      "The **Japan Meteorological Agency** releases annual cherry blossom forecasts around February. I'd recommend planning for **April 1–10** for the highest probability of full bloom.\n\n" +
      "Popular spots:\n" +
      "1. Philosopher's Path (Ginkaku-ji to Nanzen-ji)\n" +
      "2. Maruyama Park (evening illuminations)\n" +
      "3. Chidorigafuchi in Tokyo (if you extend the trip)\n\n" +
      "Want me to search flights from Dubai to Kyoto for early April?", undefined, "Reasoned for 4s"),
    m("u3", "user", "Yes, search for direct flights for 2 people"),
    m("a3", "assistant",
      "Found direct flight options for **April 5–12, 2025** (7 nights):\n\n" +
      "**Emirates EK 301**\n" +
      "- DXB → NRT (Tokyo), then domestic to KIX\n" +
      "- Depart 15:20, arrive 23:55+1\n" +
      "- Business class from AED 8,500 per person\n\n" +
      "**Japan Airlines JL 447**\n" +
      "- DXB → NRT direct\n" +
      "- Depart 03:20, arrive 14:45\n" +
      "- Economy from AED 4,200 per person\n\n" +
      "For the best experience, I'd suggest flying JAL business and then the Shinkansen from Tokyo to Kyoto (2h 15m, ~AED 200).\n\n" +
      "**[View all flights](#flights)** — Want me to add these to your calendar?", undefined, "Searched 15 flights · 5s"),
  ],

  "cover-letter-ai": [
    m("u1", "user", "Write a cover letter for an AI Engineer position at a UAE startup"),
    m("a1", "assistant",
      "Here's a tailored cover letter:\n\n---\n\n**Dear Hiring Team,**\n\n" +
      "I'm excited to apply for the AI Engineer position at your company. With 3+ years building production ML systems and a deep passion for Arabic NLP, I'm eager to contribute to [Company]'s mission of making AI accessible across the MENA region.\n\n" +
      "At my current role, I:\n" +
      "- Built a real-time sentiment analysis pipeline serving 2M+ daily requests\n" +
      "- Fine-tuned open-source LLMs for domain-specific tasks (cost reduction: 40%)\n" +
      "- Led the migration from TF serving to Triton Inference Server\n\n" +
      "What draws me to your startup is the focus on [specific product/mission]. I've followed your work on [recent launch] and believe my experience in deploying multilingual AI systems aligns well with your roadmap.\n\n" +
      "I'd love to discuss how I can contribute. My GitHub and portfolio are linked below.\n\n" +
      "Best regards,\n" +
      "[Your Name]\n\n---\n\n" +
      "Want me to customize any section for a specific company or adjust the tone?", undefined, "Reasoned for 3s"),
    m("u2", "user", "Customize it for a role at a fintech company in Dubai"),
    m("a2", "assistant",
      "Here's the revised version:\n\n---\n\n**Dear Fintech AI Team,**\n\n" +
      "I'm writing to express my interest in the AI Engineer role at your Dubai-based fintech. With a track record of building compliant ML pipelines and a keen interest in financial AI applications, I'm confident I can help scale your recommendation and risk engines.\n\n" +
      "Key achievements relevant to fintech:\n" +
      "- Deployed a fraud detection model reducing false positives by 23%\n" +
      "- Built real-time credit scoring features processing 50K transactions/hour\n" +
      "- Implemented explainable AI (SHAP values) to meet UAE Central Bank compliance\n\n" +
      "Having worked extensively with Azure OpenAI and on-prem deployments, I understand the regulatory landscape in the UAE and can ensure our AI systems meet **CBUAE guidelines** while delivering business value.\n\n" +
      "I'd welcome the opportunity to discuss how my background in both AI engineering and financial domain knowledge can accelerate your team's goals.\n\n" +
      "Warm regards,\n" +
      "[Your Name]", undefined, "Reasoned for 4s"),
  ],

  "meal-prep": [
    m("u1", "user", "Give me a healthy meal prep plan for the week — suitable for someone working long hours"),
    m("a1", "assistant",
      "Here's a 5-day meal prep plan designed for busy professionals:\n\n**Prep Day (Sunday — 2 hours)**\n\n**Batch cook these staples:**\n" +
      "1. Quinoa (3 cups cooked)\n" +
      "2. Grilled chicken breast (6 portions)\n" +
      "3. Roasted sweet potatoes\n" +
      "4. Steamed broccoli & carrots\n" +
      "5. Mediterranean salad mix (keep dressing separate)\n\n" +
      "**Weekly Layout**\n\n" +
      "**Monday:** Chicken + quinoa + roasted veggies + tahini dressing\n" +
      "**Tuesday:** Chicken wrap (whole wheat tortilla, hummus, salad)\n" +
      "**Wednesday:** Stir-fry with edamame, soy-ginger sauce\n" +
      "**Thursday:** Buddha bowl (sweet potato base, chickpeas, feta)\n" +
      "**Friday:** Leftover frittata + side salad\n\n" +
      "**Nutrition per meal (approx.)**\n" +
      "- Calories: 550–650\n" +
      "- Protein: 35–45g\n" +
      "- Prep cost: ~AED 80/week for 5 meals\n\n" +
      "Want a shopping list for this plan?", undefined, "Reasoned for 5s"),
    m("u2", "user", "Yes, and include things I can get at Carrefour UAE"),
    m("a2", "assistant",
      "Here's your Carrefour UAE shopping list:\n\n**Proteins:**\n" +
      "- Chicken breast (1.5 kg) — meat section\n" +
      "- Eggs (1 pack of 12) — dairy section\n" +
      "- Chickpeas (2 cans) — canned goods\n" +
      "- Feta cheese (200g block) — dairy\n\n" +
      "**Produce:**\n" +
      "- Sweet potatoes (1 kg)\n" +
      "- Broccoli (2 heads)\n" +
      "- Baby carrots (500g)\n" +
      "- Mixed salad greens (2 boxes)\n" +
      "- Lemons (4)\n" +
      "- Garlic (1 bulb)\n\n" +
      "**Pantry:**\n" +
      "- Quinoa (500g bag)\n" +
      "- Olive oil\n" +
      "- Tahini (1 jar)\n" +
      "- Hummus (1 tub)\n" +
      "- Whole wheat tortillas (1 pack)\n" +
      "- Soy sauce (low sodium)\n\n" +
      "**Estimated total: ~AED 75–90** at Carrefour prices. All items are standard stock — no specialty imports needed.", undefined, "Searched 3 recipes · 4s"),
  ],

  "python-photo-rename": [
    m("u1", "user", "Write a Python script to batch-rename photo files by their EXIF date"),
    m("a1", "assistant",
      "Here's a robust script using Pillow to extract EXIF dates:\n\n```python\n" +
      "import os\n" +
      "from PIL import Image\n" +
      "from datetime import datetime\n" +
      "import shutil\n" +
      "\n" +
      "def rename_photos_by_date(folder_path):\n" +
      "    for filename in os.listdir(folder_path):\n" +
      "        if not filename.lower().endswith(('.jpg', '.jpeg')):\n" +
      "            continue\n" +
      "        \n" +
      "        filepath = os.path.join(folder_path, filename)\n" +
      "        try:\n" +
      "            img = Image.open(filepath)\n" +
      "            exif_data = img._getexif()\n" +
      "            if not exif_data:\n" +
      "                continue\n" +
      "            \n" +
      "            date_tag = exif_data.get(36867)  # DateTimeOriginal\n" +
      "            if date_tag:\n" +
      "                date_str = date_tag[:10].replace(':', '-')\n" +
      "                new_name = f\"{date_str}_{filename}\"\n" +
      "                shutil.move(filepath, os.path.join(folder_path, new_name))\n" +
      "                print(f\"Renamed: {filename} -> {new_name}\")\n" +
      "        except Exception as e:\n" +
      "            print(f\"Skipped {filename}: {e}\")\n" +
      "\n" +
      "# Usage\n" +
      "rename_photos_by_date('/path/to/photos')\n" +
      "```\n\n" +
      "This preserves original filenames as a suffix, so nothing gets lost if the rename fails.\n\n" +
      "Want me to add a preview mode that shows what would be renamed without actually moving files?", undefined, "Reasoned for 3s"),
    m("u2", "user", "Yes, and also create date-based folders automatically"),
    m("a2", "assistant",
      "Here's the enhanced version:\n\n```python\n" +
      "import os\n" +
      "from PIL import Image\n" +
      "from datetime import datetime\n" +
      "import shutil\n" +
      "\n" +
      "def organize_by_date(folder_path, dry_run=True):\n" +
      "    organized = 0\n" +
      "    for filename in os.listdir(folder_path):\n" +
      "        ext = os.path.splitext(filename)[1].lower()\n" +
      "        if ext not in ('.jpg', '.jpeg', '.png'):\n" +
      "            continue\n" +
      "        \n" +
      "        filepath = os.path.join(folder_path, filename)\n" +
      "        try:\n" +
      "            img = Image.open(filepath)\n" +
      "            exif = img._getexif()\n" +
      "            date_str = exif.get(36867, '')[:10]\n" +
      "            if not date_str:\n" +
      "                continue\n" +
      "            \n" +
      "            year_month = date_str[:7]\n" +
      "            dest_folder = os.path.join(folder_path, year_month)\n" +
      "            if dry_run:\n" +
      "                print(f\"Would move: {filename} -> {dest_folder}/\")\n" +
      "            else:\n" +
      "                os.makedirs(dest_folder, exist_ok=True)\n" +
      "                shutil.move(filepath, os.path.join(dest_folder, filename))\n" +
      "            organized += 1\n" +
      "        except Exception as e:\n" +
      "            print(f\"Skipped {filename}: {e}\")\n" +
      "    \n" +
      "    mode = \"Dry run — \" if dry_run else \"\"\n" +
      "    print(f\"{mode}Processed {organized} photos\")\n" +
      "\n" +
      "# Preview first, then run for real:\n" +
      "organize_by_date('/Users/haitham/Pictures', dry_run=True)\n" +
      "# organize_by_date('/Users/haitham/Pictures', dry_run=False)\n" +
      "```\n\n" +
      "Always run with `dry_run=True` first to verify the results before moving files!", undefined, "Reasoned for 5s"),
  ],

  "golden-visa": [
    m("u1", "user", "What are the requirements for a UAE Golden Visa in 2024?"),
    m("a1", "assistant",
      "Here's a breakdown of the main **UAE Golden Visa (10-year residency)** pathways:\n\n**1. Real Estate Investor**\n" +
      "- Minimum investment: **AED 2 million** (property must be held for 3 years)\n" +
      "- Can include mortgaged property (value still counts at 2M+)\n\n" +
      "**2. Entrepreneur / Investor**\n" +
      "- Invest AED 500K+ in a business\n" +
      "- Or have a patent registered in the UAE\n\n" +
      "**3. Specialized Talent** (doctors, engineers, scientists, artists)\n" +
      "- Relevant degree + professional certification\n" +
      "- Current salary: minimum AED 30K/month\n\n" +
      "**4. Outstanding Students**\n" +
      "- Top 10 in federal exams or GPA 3.8+\n\n" +
      "**General requirements across all categories:**\n" +
      "- Valid passport (6+ months)\n" +
      "- Clean criminal record\n" +
      "- Valid UAE health insurance\n" +
      "- Medical fitness test\n\n" +
      "Processing time: **2–4 weeks**. Want me to check which category you might qualify for based on your background?", undefined, "Searched 10 sources · 8s"),
    m("u2", "user", "I'm a software engineer earning AED 25K — which path should I consider?"),
    m("a2", "assistant",
      "Based on your profile, here are your best options:\n\n**Option 1: Real Estate Investor**\n" +
      "- If you can invest AED 2M in property, this is the fastest route\n" +
      "- You can buy a studio in areas like Dubailand or International City\n" +
      "- Rental yield: ~5–7% annually\n\n" +
      "**Option 2: Freelance / Self-Employment Visa**\n" +
      "- Get a freelance permit from TAMM (AED 7K–15K)\n" +
      "- Requires proof of income (your AED 25K salary may qualify)\n" +
      "- Gives you 2-year renewable visa (not 10-year yet, but a step toward it)\n\n" +
      "**Option 3: Skilled Worker (upgrade path)**\n" +
      "- Work toward AED 30K/month salary at your current company or a new role\n" +
      "- Once you hit 30K, you qualify for the specialized talent Golden Visa\n" +
      "- Some companies in UAE offer salary bumps for Golden Visa retention bonuses\n\n" +
      "My recommendation: **start with Option 2** (freelance permit) while working toward Option 3 (salary increase). This gives you flexibility now and a clear 10-year path.", undefined, "Reasoned for 6s"),
  ],

  "mom-birthday-gift": [
    m("u1", "user", "Give me gift ideas for my mom's birthday — she's in her 50s, loves reading and coffee"),
    m("a1", "assistant",
      "Here are curated gift ideas within **AED 200–400**:\n\n**Personalized & Practical**\n" +
      "1. **Leather-bound journal + pen set** — AED 150–250 at Jarir or Bloomingdale's\n" +
      "2. **Book subscription box** — The Book Depot UAE (monthly curated picks)\n" +
      "3. **Personalized photo book** — Snapfish UAE, upload family photos\n\n" +
      "**Coffee Lover Gifts**\n" +
      "4. **AeroPress + specialty beans** — ~AED 180 at The Coffee House Dubai\n" +
      "5. **Japanese ceramic pour-over set** — AED 200–300 at Arabesque\n" +
      "6. **Electric gooseneck kettle** — AED 150 at Amazon.ae\n\n" +
      "**Experience Gifts**\n" +
      "7. **Coffee tasting session** at a specialty roastery — ~AED 120\n" +
      "8. **Spa day voucher** — Gold's Gym or local wellness centers\n" +
      "9. **Tickets to a museum or art exhibition** — Etihad Museum, Louvre Abu Dhabi\n\n" +
      "Want me to find specific prices and availability for any of these?", undefined, "Searched 12 stores · 6s"),
    m("u2", "user", "I want the AeroPress combo — where in Dubai can I buy it today?"),
    m("a2", "assistant",
      "You can pick up the AeroPress at these Dubai locations today:\n\n**1. The Coffee House** — Dubai Mall, Level 2 (next to Starbucks)\n" +
      "- AeroPress Original: AED 165\n" +
      "- Filter pack (100): AED 45\n\n" +
      "**2. Beans & Bean** — Various locations (Marina, JBR, City Walk)\n" +
      "- AeroPress: AED 170\n" +
      "- Their house blend beans (250g): AED 55\n\n" +
      "**3. Amazon.ae**\n" +
      "- Prime delivery available today if you order within 2 hours\n" +
      "- AeroPress Grant: AED 195 (the upgraded version with metal filter)\n\n" +
      "My pick: Go to **Beans & Bean at City Walk** — they let you taste the coffee before buying and the staff is very knowledgeable about brewing methods.", undefined, "Searched 5 stores · 3s"),
  ],

  "langgraph-learning": [
    m("u1", "user", "Create a 6-week learning plan for LangGraph"),
    m("a1", "assistant",
      "Here's a structured 6-week LangGraph roadmap:\n\n**Week 1–2: Foundations**\n" +
      "1. Complete the official [LangGraph documentation](https://langchain-ai.github.io/langgraph/)\n" +
      "2. Build a simple chatbot with `StateGraph`\n" +
      "3. Understand nodes, edges, and conditional routing\n\n" +
      "**Week 3: Tool Calling & Agents**\n" +
      "1. Implement tool calling in a graph\n" +
      "2. Build a multi-tool agent (search + calculate)\n" +
      "3. Learn `ToolNode` and response parsing\n\n" +
      "**Week 4: Human-in-the-Loop**\n" +
      "1. Add approval gates (`interrupt()`) to your graphs\n" +
      "2. Implement state checkpointing\n" +
      "3. Build a review workflow with human feedback\n\n" +
      "**Week 5: Advanced Patterns**\n" +
      "1. Nested subgraphs for modular design\n" +
      "2. Parallel execution with `Fanout`/`FanIn`\n" +
      "3. Streaming responses with `astream_events`\n\n" +
      "**Week 6: Production Deployment**\n" +
      "1. Deploy on LangGraph Cloud or FastAPI\n" +
      "2. Add observability (LangSmith traces)\n" +
      "3. Build a production-grade customer support agent\n\n" +
      "Want me to generate a starter notebook for Week 1?", undefined, "Reasoned for 7s"),
    m("u2", "user", "Yes, and include practice exercises"),
    m("a2", "assistant",
      "Here's the Week 1 starter with exercises:\n\n```python\n" +
      "# week1_starter.py\n" +
      "from langgraph.graph import StateGraph, START, END\n" +
      "from typing import TypedDict\n" +
      "\n" +
      "class GraphState(TypedDict):\n" +
      "    messages: list\n" +
      "    score: int\n" +
      "\n" +
      "def chat_node(state: GraphState) -> GraphState:\n" +
      "    # Your turn: call an LLM here\n" +
      "    response = \"TODO: implement LLM call\"\n" +
      "    state['messages'].append({'role': 'assistant', 'content': response})\n" +
      "    return state\n" +
      "\n" +
      "def score_node(state: GraphState) -> GraphState:\n" +
      "    # Your turn: rate the response quality\n" +
      "    state['score'] = 0  # TODO\n" +
      "    return state\n" +
      "\n" +
      "graph = StateGraph(GraphState)\n" +
      "graph.add_node('chat', chat_node)\n" +
      "graph.add_node('score', score_node)\n" +
      "graph.add_edge(START, 'chat')\n" +
      "graph.add_edge('chat', 'score')\n" +
      "graph.add_edge('score', END)\n" +
      "\n" +
      "app = graph.compile()\n" +
      "```\n\n" +
      "**Exercises:**\n" +
      "1. Connect `chat_node` to an actual LLM (use `ChatOpenAI`)\n" +
      "2. Add a condition: if `score < 5`, loop back to `chat_node` with a rewrite prompt\n" +
      "3. Add memory using `MemorySaver` to persist conversation history\n\n" +
      "Full solution with answers will be in the next session. Keep going!", undefined, "Reasoned for 4s"),
  ],

  "london-weather": [
    m("u1", "user", "What's the weather forecast for London next week?"),
    m("a1", "assistant",
      "Here's the 7-day forecast for London:\n\n**Today** — Partly cloudy, 14°C / 8°C · Light rain expected in the evening\n\n**Tomorrow** — Overcast, 13°C / 7°C\n\n**Wednesday** — Clear skies, 15°C / 9°C — best day of the week\n\n**Thursday** — Showers, 12°C / 8°C\n\n**Friday** — Windy, 11°C / 6°C\n\n**Saturday** — Cloudy with breaks, 13°C / 7°C\n\n**Sunday** — Rain likely, 10°C / 5°C\n\n**Tips for your trip:**\n" +
      "- Pack layers — temperatures swing 5–8°C between day and night\n" +
      "- Waterproof jacket is essential (it rains ~12 days this month)\n" +
      "- Wednesday looks like the best day for outdoor activities\n\n" +
      "**[Open Weather](#weather)** — Want me to add anything to your calendar?", undefined, "Fetched live data · 2s"),
  ],

  "resume-feedback": [
    m("u1", "user", "Give me feedback on my resume for ML engineering roles in the UAE"),
    m("a1", "assistant",
      "Here's targeted feedback for ML engineering resumes in the UAE market:\n\n**Strengths to highlight:**\n" +
      "1. **Production deployment experience** — UAE employers value operators who can ship, not just experiment\n" +
      "2. **Multilingual capability** — Arabic NLP is a differentiator in the region\n" +
      "3. **Cloud certifications** — Azure AI or AWS ML specialty carry weight\n\n" +
      "**Common gaps I see:**\n" +
      "- Leading with academic projects instead of production metrics\n" +
      "- Not quantifying impact (e.g., \"reduced inference latency by 40%\" instead of \"optimized models\")\n" +
      "- Missing keywords that ATS systems scan for in the UAE: **MLOps, Triton, ONNX, LangChain, vector databases**\n\n" +
      "**Suggested structure:**\n" +
      "1. Summary (2 lines max, mention years + specialization)\n" +
      "2. Technical skills (grouped: Languages / Frameworks / Cloud / MLOps)\n" +
      "3. Experience (bullet format: action verb + metric + tool)\n" +
      "4. Projects (only if they demonstrate production readiness)\n\n" +
      "Want me to rewrite a specific bullet point for you?", undefined, "Reasoned for 5s"),
    m("u2", "user", "Rewrite this: \"Built ML models for a project\""),
    m("a2", "assistant",
      "Here are stronger alternatives:\n\n**Before:**\n" +
      "> \"Built ML models for a project\"\n\n" +
      "**After (pick one):**\n" +
      "- \"Designed and deployed a real-time sentiment analysis pipeline serving **2M+ daily API calls** with 94% accuracy, reducing manual moderation costs by **35%**\"\n" +
      "- \"Led the end-to-end development of a customer churn prediction model, achieving **AUC 0.89** and preventing an estimated **$200K** in monthly revenue loss\"\n" +
      "- \"Migrated legacy TF serving infrastructure to **Triton Inference Server**, cutting P99 latency from 450ms to **120ms** and supporting **3x** traffic growth\"\n\n" +
      "The key pattern: **action verb + metric + business impact + tool**. Pick whichever achievement is closest to your actual work and customize the numbers.", undefined, "Reasoned for 3s"),
  ],
};

// Return a fresh shallow copy of each message so mutations don't affect the fixtures
export const getDemoMessages = (id: string): AiMessage[] => {
  const t = threads[id];
  if (!t) return [];
  return t.map((msg) => ({ ...msg }));
};
