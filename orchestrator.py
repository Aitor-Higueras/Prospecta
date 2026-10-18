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
    def __init__(self, niche: str, value_proposition: str, tone: str):
        self.niche = niche
        self.value_proposition = value_proposition
        self.tone = tone

        # LLM Base: Google Gemini 3.1 Flash Lite Preview (Lo más nuevo de 2026)
        self.gemini_llm = LLM(
            model="gemini/gemini-3.1-flash-lite-preview",
            temperature=0.2,
            api_key=os.environ.get("GOOGLE_API_KEY", "")
        )

        # LLM Secundario: Llama 3.1 por Groq
        groq_api_key = os.environ.get("GROQ_API_KEY", "")
        if groq_api_key and groq_api_key != "your_groq_api_key_here" and groq_api_key != "":
            try:
                self.copy_llm = LLM(
                    model="groq/llama-3.1-70b-versatile",
                    temperature=0.7, 
                    api_key=groq_api_key
                )
            except Exception:
                self.copy_llm = self.gemini_llm
        else:
            self.copy_llm = self.gemini_llm

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
            llm=self.gemini_llm,
            verbose=True,
            allow_delegation=False
        )

        website_researcher = Agent(
            config=agents_config['website_researcher'],
            tools=[scrape_website, search_internet],
            llm=self.gemini_llm,
            verbose=True,
            allow_delegation=False
        )

        qualifier = Agent(
            config=agents_config['qualifier'],
            llm=self.gemini_llm,
            verbose=True,
            allow_delegation=False
        )

        sales_strategist = Agent(
            config=agents_config['sales_strategist'],
            llm=self.gemini_llm,
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
