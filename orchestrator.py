import os
import yaml
import pandas as pd
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

from tools.search_tool import search_internet
from tools.scraper_tool import scrape_website

# Instanciar load_dotenv globalmente no hace daño para modo local
load_dotenv()

class SDRCrew:
    def __init__(
        self,
        niche: str,
        value_proposition: str,
        tone: str,
        ai_model: str = None,
        api_key: str = None,
        ai_base_url: str = None
    ):
        self.niche = niche
        self.value_proposition = value_proposition
        self.tone = tone

        # Determinar modelo (por defecto Gemini 2.5 Flash)
        self.model = ai_model or os.environ.get("AI_MODEL", "gemini/gemini-2.5-flash")
        
        # Determinar API Key con fallbacks inteligentes según el prefijo del modelo
        self.api_key = api_key
        if not self.api_key:
            if "gemini" in self.model:
                self.api_key = os.environ.get("GOOGLE_API_KEY", "")
            elif "openai" in self.model or "gpt" in self.model:
                self.api_key = os.environ.get("OPENAI_API_KEY", "")
            elif "claude" in self.model or "anthropic" in self.model:
                self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            elif "deepseek" in self.model:
                self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            elif "groq" in self.model:
                self.api_key = os.environ.get("GROQ_API_KEY", "")
            elif "mistral" in self.model:
                self.api_key = os.environ.get("MISTRAL_API_KEY", "")
            else:
                self.api_key = os.environ.get("AI_API_KEY", "")

        # Configurar LLM principal (análisis y búsqueda)
        llm_kwargs = {
            "model": self.model,
            "temperature": 0.2
        }
        if self.api_key:
            llm_kwargs["api_key"] = self.api_key
        if ai_base_url:
            llm_kwargs["base_url"] = ai_base_url

        self.main_llm = LLM(**llm_kwargs)

        # Configurar LLM para redacción de copy (temperatura más alta para mayor creatividad)
        copy_kwargs = llm_kwargs.copy()
        copy_kwargs["temperature"] = 0.6
        self.copy_llm = LLM(**copy_kwargs)

    def run(self):
        # 1. Cargar la configuración de Agentes y Tareas desde YAML
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        with open(os.path.join(base_dir, 'config', 'agents.yaml'), 'r', encoding='utf-8') as f:
            agents_config = yaml.safe_load(f)
            
        with open(os.path.join(base_dir, 'config', 'tasks.yaml'), 'r', encoding='utf-8') as f:
            tasks_config = yaml.safe_load(f)

        # 2. Construir los Agentes de la Crew
        lead_finder = Agent(
            config=agents_config['lead_finder'],
            tools=[search_internet],
            llm=self.main_llm,
            verbose=True,
            allow_delegation=False
        )

        website_researcher = Agent(
            config=agents_config['website_researcher'],
            tools=[scrape_website, search_internet],
            llm=self.main_llm,
            verbose=True,
            allow_delegation=False
        )

        qualifier = Agent(
            config=agents_config['qualifier'],
            llm=self.main_llm,
            verbose=True,
            allow_delegation=False
        )

        sales_strategist = Agent(
            config=agents_config['sales_strategist'],
            llm=self.main_llm,
            verbose=True,
            allow_delegation=False
        )

        copywriter_elite = Agent(
            config=agents_config['copywriter_elite'],
            llm=self.copy_llm, 
            verbose=True,
            allow_delegation=False
        )

        # 3. Construir las Tareas
        find_leads = Task(
            config=tasks_config['find_leads_task'],
            agent=lead_finder
        )

        research_company = Task(
            config=tasks_config['research_company_task'],
            agent=website_researcher,
            context=[find_leads]
        )

        qualify_lead = Task(
            config=tasks_config['qualify_lead_task'],
            agent=qualifier,
            context=[research_company]
        )

        strategize_pitch = Task(
            config=tasks_config['strategize_pitch_task'],
            agent=sales_strategist,
            context=[qualify_lead, research_company]
        )

        write_email = Task(
            config=tasks_config['write_email_task'],
            agent=copywriter_elite,
            context=[strategize_pitch, research_company]
        )

        # 4. Formar y ejecutar la Crew en modo secuencial
        crew = Crew(
            agents=[lead_finder, website_researcher, qualifier, sales_strategist, copywriter_elite],
            tasks=[find_leads, research_company, qualify_lead, strategize_pitch, write_email],
            process=Process.sequential,
            verbose=True,
            memory=False
        )

        # Input injection al iniciar
        result = crew.kickoff(inputs={
            'niche': self.niche,
            'value_proposition': self.value_proposition,
            'tone': self.tone
        })

        # 5. Guardar resultado en un archivo persistente (Log de Prospección)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_niche = "".join(c for c in self.niche if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"prospeccion_{safe_niche}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(result))
            print(f"--- Prospección guardada en {filename} ---")
        except Exception as e:
            print(f"Error al guardar el log: {e}")

        return result
