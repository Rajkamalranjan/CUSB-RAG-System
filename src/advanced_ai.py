"""
Advanced AI Components for CUSB RAG System
Multi-modal RAG + Agentic System + Fine-tuning Support
"""

import base64
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

import numpy as np
from PIL import Image


# ==================== Multi-Modal RAG ====================

@dataclass
class MultimodalContent:
    """Container for multimodal content."""
    text: Optional[str] = None
    images: List[Dict] = None
    tables: List[Dict] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.tables is None:
            self.tables = []
        if self.metadata is None:
            self.metadata = {}


class ImageProcessor:
    """Process and index images for retrieval."""
    
    def __init__(self):
        self.image_index = []
    
    def extract_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """Extract images from PDF files."""
        images = []
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list, start=1):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Get image description (could use vision model)
                    images.append({
                        "page": page_num + 1,
                        "index": img_index,
                        "bytes": image_bytes,
                        "ext": base_image["ext"],
                        "description": f"Image on page {page_num + 1}"
                    })
            
            doc.close()
        except ImportError:
            print("PyMuPDF not installed. Skipping PDF image extraction.")
        
        return images
    
    def process_image(self, image_data: bytes) -> Dict:
        """Process single image for indexing."""
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # Extract basic metadata
            return {
                "size": img.size,
                "mode": img.mode,
                "format": img.format,
                "thumbnail": self._create_thumbnail(image_data)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _create_thumbnail(self, image_data: bytes, size=(150, 150)) -> str:
        """Create base64 thumbnail."""
        try:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail(size)
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue()).decode()
        except:
            return ""


class TableExtractor:
    """Extract and index tables from documents."""
    
    def __init__(self):
        self.tables = []
    
    def extract_from_html(self, html_content: str) -> List[Dict]:
        """Extract tables from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = []
        
        for i, table in enumerate(soup.find_all('table')):
            rows = []
            for tr in table.find_all('tr'):
                row_data = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if row_data:
                    rows.append(row_data)
            
            if rows:
                tables.append({
                    "table_id": i,
                    "headers": rows[0] if rows else [],
                    "data": rows[1:] if len(rows) > 1 else [],
                    "caption": self._extract_caption(table)
                })
        
        return tables
    
    def _extract_caption(self, table) -> str:
        """Extract table caption."""
        # Look for preceding text that might be caption
        prev = table.find_previous_sibling()
        if prev and prev.name in ['p', 'h2', 'h3', 'h4']:
            return prev.get_text(strip=True)
        return ""


# ==================== Agentic RAG System ====================

class Tool:
    """Tool for agent to use."""
    
    def __init__(self, name: str, description: str, function: Callable):
        self.name = name
        self.description = description
        self.function = function
    
    def execute(self, **kwargs) -> Any:
        """Execute tool."""
        return self.function(**kwargs)


class Agent:
    """Agent that can use tools and reason."""
    
    def __init__(self, name: str, llm, tools: List[Tool] = None):
        self.name = name
        self.llm = llm
        self.tools = tools or []
        self.memory = []
        self.max_iterations = 5
    
    def think(self, query: str, context: str = "") -> Dict:
        """Think about how to answer query."""
        
        # Determine if tools needed
        needs_tools = self._needs_tools(query)
        
        if needs_tools and self.tools:
            # Plan with tools
            plan = self._create_plan(query)
            
            # Execute plan
            results = []
            for step in plan:
                tool_result = self._execute_tool_step(step)
                results.append(tool_result)
            
            # Generate final answer
            answer = self._synthesize(query, results, context)
            
            return {
                "answer": answer,
                "plan": plan,
                "tool_results": results,
                "reasoning": self._get_reasoning_trace()
            }
        else:
            # Direct answer
            answer = self._direct_answer(query, context)
            return {
                "answer": answer,
                "plan": [],
                "tool_results": [],
                "reasoning": "Direct retrieval and generation"
            }
    
    def _needs_tools(self, query: str) -> bool:
        """Determine if query needs tool usage."""
        tool_keywords = [
            "calculate", "compare", "list all", "find", "search for",
            "when is", "contact", "phone", "email", "apply", "deadline"
        ]
        return any(kw in query.lower() for kw in tool_keywords)
    
    def _create_plan(self, query: str) -> List[Dict]:
        """Create execution plan."""
        # Simple planning - can be enhanced with LLM
        plan = []
        
        if "fee" in query.lower() or "cost" in query.lower():
            plan.append({"tool": "fee_lookup", "params": {"course": query}})
        
        if "contact" in query.lower() or "phone" in query.lower():
            plan.append({"tool": "contact_lookup", "params": {"department": query}})
        
        if "compare" in query.lower():
            plan.append({"tool": "comparison", "params": {"items": query}})
        
        return plan
    
    def _execute_tool_step(self, step: Dict) -> Dict:
        """Execute a tool step."""
        tool_name = step.get("tool")
        params = step.get("params", {})
        
        tool = next((t for t in self.tools if t.name == tool_name), None)
        
        if tool:
            try:
                result = tool.execute(**params)
                return {"tool": tool_name, "status": "success", "result": result}
            except Exception as e:
                return {"tool": tool_name, "status": "error", "error": str(e)}
        
        return {"tool": tool_name, "status": "not_found"}
    
    def _synthesize(self, query: str, results: List[Dict], context: str) -> str:
        """Synthesize final answer."""
        # Combine tool results with context
        combined = context + "\n\nAdditional information:\n"
        for r in results:
            if r["status"] == "success":
                combined += f"\n- {r['tool']}: {r['result']}"
        
        # Generate answer
        prompt = f"""Based on the following information, answer the query:

Query: {query}

Information:
{combined}

Provide a clear, accurate answer."""
        
        return self.llm.generate(prompt)
    
    def _direct_answer(self, query: str, context: str) -> str:
        """Generate direct answer."""
        prompt = f"""Answer the following query based on the context:

Query: {query}

Context:
{context}

Answer:"""
        
        return self.llm.generate(prompt)
    
    def _get_reasoning_trace(self) -> str:
        """Get reasoning trace."""
        return " -> ".join([m.get("action", "") for m in self.memory])


# ==================== Fine-tuning Support ====================

class TrainingDataGenerator:
    """Generate training data for fine-tuning."""
    
    def __init__(self, rag_pipeline):
        self.rag_pipeline = rag_pipeline
        self.training_examples = []
    
    def generate_qa_pairs(self, chunks: List[Dict], num_questions_per_chunk: int = 3) -> List[Dict]:
        """Generate Q&A pairs from chunks."""
        qa_pairs = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            if len(text) < 100:
                continue
            
            # Generate questions (simplified - can use LLM)
            questions = self._generate_questions(text, num_questions_per_chunk)
            
            for q in questions:
                # Get answer from RAG
                response = self.rag_pipeline.answer(q)
                
                qa_pairs.append({
                    "instruction": q,
                    "input": "",
                    "output": response.get("answer", ""),
                    "context": text[:500],
                    "source_chunk": chunk.get("id")
                })
        
        return qa_pairs
    
    def _generate_questions(self, text: str, n: int) -> List[str]:
        """Generate questions from text."""
        # Simple question templates
        templates = [
            "What is mentioned about {}?",
            "Tell me about {}.",
            "What are the details of {}?",
            "Explain {}.",
            "What information is available about {}?"
        ]
        
        # Extract key phrases (simplified)
        sentences = text.split('.')
        questions = []
        
        for i, sent in enumerate(sentences[:n]):
            # Extract key phrase (first few words)
            words = sent.strip().split()[:5]
            if len(words) > 3:
                key_phrase = " ".join(words)
                template = templates[i % len(templates)]
                questions.append(template.format(key_phrase))
        
        return questions
    
    def save_training_data(self, output_path: Path, format: str = "alpaca"):
        """Save in format for fine-tuning."""
        if format == "alpaca":
            data = self.training_examples
        elif format == "sharegpt":
            data = self._convert_to_sharegpt()
        else:
            data = self.training_examples
        
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Training data saved: {output_path}")
    
    def _convert_to_sharegpt(self) -> List[Dict]:
        """Convert to ShareGPT format."""
        sharegpt_data = []
        
        for ex in self.training_examples:
            sharegpt_data.append({
                "conversations": [
                    {"from": "human", "value": ex["instruction"]},
                    {"from": "gpt", "value": ex["output"]}
                ]
            })
        
        return sharegpt_data


class ModelFineTuner:
    """Fine-tune models on CUSB domain."""
    
    def __init__(self, base_model: str = "meta-llama/Llama-2-7b-hf"):
        self.base_model = base_model
        self.training_config = {
            "num_epochs": 3,
            "batch_size": 4,
            "learning_rate": 2e-4,
            "lora_r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "v_proj"]
        }
    
    def prepare_for_qlora(self, training_data: List[Dict]):
        """Prepare QLoRA fine-tuning configuration."""
        config = {
            "model_name": self.base_model,
            "training_data": training_data,
            "lora_config": {
                "r": self.training_config["lora_r"],
                "lora_alpha": self.training_config["lora_alpha"],
                "target_modules": self.training_config["target_modules"],
                "lora_dropout": 0.05,
                "bias": "none",
                "task_type": "CAUSAL_LM"
            },
            "training_args": {
                "num_train_epochs": self.training_config["num_epochs"],
                "per_device_train_batch_size": self.training_config["batch_size"],
                "learning_rate": self.training_config["learning_rate"],
                "warmup_steps": 100,
                "logging_steps": 10,
                "save_strategy": "epoch",
                "fp16": True,
                "gradient_accumulation_steps": 4,
                "optim": "paged_adamw_8bit"
            }
        }
        
        return config
    
    def create_training_script(self, output_path: Path):
        """Create training script template."""
        script = '''#!/usr/bin/env python3
"""
Fine-tune LLM on CUSB domain data using QLoRA
"""

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig
)
from trl import SFTTrainer
import torch

# Load model with 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

# Prepare for training
model = prepare_model_for_kbit_training(model)

# Add LoRA adapters
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer.pad_token = tokenizer.eos_token

# Training arguments
training_args = TrainingArguments(
    output_dir="./cusb_llama_finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    optim="paged_adamw_8bit",
    learning_rate=2e-4,
    warmup_steps=100,
    logging_steps=10,
    save_strategy="epoch",
    fp16=True,
)

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,  # Load your dataset here
    dataset_text_field="text",
    max_seq_length=512,
    args=training_args,
)

trainer.train()
model.save_pretrained("./cusb_llama_finetuned")
'''
        
        with open(output_path, 'w') as f:
            f.write(script)
        
        print(f"✅ Training script saved: {output_path}")


# ==================== Query Expansion & Advanced Retrieval ====================

class QueryExpander:
    """Expand queries for better retrieval."""
    
    def __init__(self):
        self.expansion_templates = {
            "fee": ["fees", "cost", "price", "charges", "tuition"],
            "admission": ["admission", "apply", "application", "entrance", "CUET"],
            "faculty": ["faculty", "professor", "teacher", "HOD", "head"],
            "course": ["course", "programme", "program", "degree", "syllabus"],
            "hostel": ["hostel", "accommodation", "stay", "residence", "mess"],
        }
    
    def expand(self, query: str) -> List[str]:
        """Expand query with synonyms."""
        variations = [query]
        
        for key, synonyms in self.expansion_templates.items():
            if key in query.lower():
                for syn in synonyms:
                    if syn not in query.lower():
                        variations.append(query.replace(key, syn))
        
        return variations[:5]  # Limit to 5 variations
    
    def hyde(self, query: str, llm) -> str:
        """Hypothetical Document Embedding (HyDE)."""
        """Generate hypothetical answer for better retrieval."""
        prompt = f"""Given the query: "{query}"

Write a brief hypothetical document that would answer this query.
Assume the document contains factual information from CUSB university."""
        
        hypothetical_doc = llm.generate(prompt, max_tokens=200)
        return hypothetical_doc


class Reranker:
    """Re-rank retrieved documents."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Lazy load model."""
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(self.model_name)
            except:
                print(f"Could not load reranker: {self.model_name}")
    
    def rerank(self, query: str, documents: List[Dict], top_k: int = 5) -> List[Dict]:
        """Re-rank documents by relevance."""
        if not self.model or not documents:
            return documents[:top_k]
        
        # Create pairs
        pairs = [[query, doc.get("text", "")] for doc in documents]
        
        # Get scores
        scores = self.model.predict(pairs)
        
        # Sort by score
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k
        reranked = []
        for doc, score in scored_docs[:top_k]:
            doc["rerank_score"] = float(score)
            reranked.append(doc)
        
        return reranked


# ==================== Main Advanced AI Class ====================

class AdvancedRAG:
    """Advanced RAG with all features."""
    
    def __init__(self, rag_pipeline, llm):
        self.rag = rag_pipeline
        self.llm = llm
        
        # Initialize components
        self.query_expander = QueryExpander()
        self.reranker = Reranker()
        self.agent = Agent("CUSB_Agent", llm, tools=self._create_tools())
        self.image_processor = ImageProcessor()
        self.table_extractor = TableExtractor()
        self.training_generator = TrainingDataGenerator(rag_pipeline)
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for agent."""
        return [
            Tool(
                name="fee_lookup",
                description="Look up course fees",
                function=self._lookup_fees
            ),
            Tool(
                name="contact_lookup",
                description="Find contact information",
                function=self._lookup_contacts
            ),
            Tool(
                name="comparison",
                description="Compare courses or departments",
                function=self._compare_items
            )
        ]
    
    def _lookup_fees(self, course: str) -> str:
        """Tool: Look up fees."""
        result = self.rag.answer(f"{course} fees")
        return result.get("answer", "Fee information not found")
    
    def _lookup_contacts(self, department: str) -> str:
        """Tool: Look up contacts."""
        result = self.rag.answer(f"{department} contact")
        return result.get("answer", "Contact information not found")
    
    def _compare_items(self, items: str) -> str:
        """Tool: Compare items."""
        # Parse comparison query
        return f"Comparison of {items} requires detailed analysis"
    
    def query(self, question: str, use_agent: bool = True, use_reranker: bool = True) -> Dict:
        """Advanced query with all features."""
        
        # Step 1: Expand query
        expanded_queries = self.query_expander.expand(question)
        
        # Step 2: Retrieve for all variations
        all_contexts = []
        for q in expanded_queries:
            contexts = self.rag.search(q, k=3)
            all_contexts.extend(contexts)
        
        # Remove duplicates
        seen = set()
        unique_contexts = []
        for ctx in all_contexts:
            ctx_id = ctx.get("id", hash(ctx.get("text", "")))
            if ctx_id not in seen:
                seen.add(ctx_id)
                unique_contexts.append(ctx)
        
        # Step 3: Re-rank if enabled
        if use_reranker:
            contexts = self.reranker.rerank(question, unique_contexts, top_k=5)
        else:
            contexts = unique_contexts[:5]
        
        # Step 4: Agent or Direct answering
        if use_agent:
            context_text = "\n\n".join([c.get("text", "") for c in contexts])
            result = self.agent.think(question, context_text)
            answer = result["answer"]
            reasoning = result["reasoning"]
        else:
            result = self.rag.answer(question, contexts)
            answer = result.get("answer", "")
            reasoning = "Direct retrieval"
        
        return {
            "answer": answer,
            "contexts": contexts,
            "expanded_queries": expanded_queries,
            "reasoning": reasoning,
            "tools_used": result.get("tool_results", []) if use_agent else []
        }


# ==================== Usage Example ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🤖 ADVANCED AI COMPONENTS FOR CUSB RAG")
    print("=" * 70)
    print("\nComponents available:")
    print("  1. MultimodalRAG - Image & table processing")
    print("  2. AgenticRAG - Tool-using agent system")
    print("  3. Query Expansion - HyDE + synonym expansion")
    print("  4. Re-ranking - Cross-encoder reranking")
    print("  5. Fine-tuning Support - QLoRA training prep")
    print("\nIntegration:")
    print("  from advanced_ai import AdvancedRAG")
    print("  advanced = AdvancedRAG(rag_pipeline, llm)")
    print("  result = advanced.query('M.Sc fees comparison', use_agent=True)")
    print("\n" + "=" * 70)
