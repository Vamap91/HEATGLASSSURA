import streamlit as st
st.set_page_config(page_title="MonitorAI (PRD)", page_icon="🔴", layout="centered")

from openai import OpenAI
import tempfile
import re
import json
import base64
from datetime import datetime
from fpdf import FPDF

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def create_pdf(analysis, transcript_text, model_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_fill_color(193, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "MonitorAI - Relatorio de Atendimento", 1, 1, "C", True)
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
    pdf.cell(0, 10, f"Modelo: {model_name}", 0, 1)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Status Final", 0, 1)
    pdf.set_font("Arial", "", 12)
    final = analysis.get("status_final", {})
    pdf.cell(0, 10, f"Cliente: {final.get('satisfacao', 'N/A')}", 0, 1)
    pdf.cell(0, 10, f"Desfecho: {final.get('desfecho', 'N/A')}", 0, 1)
    pdf.cell(0, 10, f"Risco: {final.get('risco', 'N/A')}", 0, 1)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Script de Encerramento", 0, 1)
    pdf.set_font("Arial", "", 12)
    script_info = analysis.get("uso_script", {})
    pdf.cell(0, 10, f"Status: {script_info.get('status', 'N/A')}", 0, 1)
    pdf.multi_cell(0, 10, f"Justificativa: {script_info.get('justificativa', 'N/A')}")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Pontuacao Total", 0, 1)
    pdf.set_font("Arial", "B", 12)
    total = analysis.get("pontuacao_total", "N/A")
    pdf.cell(0, 10, f"{total} pontos de 86 (avaliacao por grupos)", 0, 1)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Resumo Geral", 0, 1)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, analysis.get("resumo_geral", "N/A"))
    pdf.ln(5)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Checklist Tecnico", 0, 1)
    pdf.ln(5)
    checklist = analysis.get("checklist", [])
    for item in checklist:
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 10, f"{item.get('item')}. {item.get('criterio')} ({item.get('pontos')} pts)")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Resposta: {item.get('resposta', '')}", 0, 1)
        pdf.multi_cell(0, 10, f"Justificativa: {item.get('justificativa', '')}")
        pdf.ln(5)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Transcricao", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 10, transcript_text)
    return pdf.output(dest="S").encode("latin1")

def get_pdf_download_link(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Baixar Relatório em PDF</a>'

def extract_json(text):
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        try:
            return json.loads(text[start_idx:end_idx+1])
        except:
            pass
    raise ValueError("Não foi possível extrair JSON válido")

st.markdown("""
<style>
h1, h2, h3 { color: #C10000 !important; }
.result-box { background-color: #ffecec; padding: 1em; border-left: 5px solid #C10000; border-radius: 6px; }
.stButton>button { background-color: #C10000; color: white; border-radius: 6px; padding: 0.4em 1em; }
.status-box { padding: 15px; border-radius: 8px; margin-bottom: 15px; background-color: #ffecec; border: 1px solid #C10000; }
.script-usado { background-color: #e6ffe6; padding: 10px; border-left: 5px solid #00C100; border-radius: 6px; }
.script-nao-usado { background-color: #ffcccc; padding: 10px; border-left: 5px solid #FF0000; border-radius: 6px; }
.criterio-sim { background-color: #e6ffe6; padding: 10px; border-radius: 6px; border-left: 5px solid #00C100; }
.criterio-nao { background-color: #ffcccc; padding: 10px; border-radius: 6px; border-left: 5px solid #FF0000; }
.progress-high { color: #00C100; }
.progress-medium { color: #FFD700; }
.progress-low { color: #FF0000; }
.criterio-eliminatorio { background-color: #ffcccc; padding: 10px; border-radius: 6px; margin-top: 20px; border: 2px solid #FF0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def get_progress_class(value):
    if value >= 70: return "progress-high"
    elif value >= 50: return "progress-medium"
    else: return "progress-low"

def get_script_status_class(status):
    if status.lower() in ["completo", "sim"]: return "script-usado"
    else: return "script-nao-usado"

modelo_gpt = "gpt-4o"

st.title("MonitorAI SURA (New)")
st.write("Análise inteligente de ligações: avaliação de atendimento ao cliente e conformidade com processos.")

uploaded_file = st.file_uploader("Envie o áudio da ligação (.mp3)", type=["mp3"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.audio(uploaded_file, format='audio/mp3')

    if st.button("🔍 Analisar Atendimento"):
        with st.spinner("Transcrevendo o áudio..."):
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            transcript_text = transcript.text

        with st.expander("Ver transcrição completa"):
            st.code(transcript_text, language="markdown")

        prompt = f"""
Você é um especialista em atendimento ao cliente da Carglass. Avalie a transcrição:

TRANSCRIÇÃO:
\"\"\"{transcript_text}\"\"\"

⚠️ LÓGICA DE GRUPOS - REGRA CRÍTICA:
Se QUALQUER item dentro de um grupo receber "não", TODO O GRUPO recebe 0 pontos.

GRUPO 1 (26pts): itens 1,3,4,5,6
GRUPO 2 (30pts): itens 7,9,10
GRUPO 3 (9pts): itens 11,12
GRUPO 4 (21pts): itens 14,15
TOTAL: 86 pontos

Retorne APENAS JSON (sem ``` ou texto):

{{
  "status_final": {{"satisfacao": "...", "risco": "...", "desfecho": "..."}},
  "checklist": [
    {{"item": 1, "criterio": "Atendeu prontamente com saudação correta", "pontos": 10, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 3, "criterio": "Confirmou cadastro e pediu 2 telefones", "pontos": 6, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 4, "criterio": "Verbalizou script LGPD", "pontos": 2, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 5, "criterio": "Utilizou técnica do eco", "pontos": 5, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 6, "criterio": "Escutou atentamente", "pontos": 3, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 7, "criterio": "Compreendeu e demonstrou domínio", "pontos": 5, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 9, "criterio": "Confirmou danos no veículo", "pontos": 10, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 10, "criterio": "Confirmou cidade", "pontos": 10, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 11, "criterio": "Comunicação eficaz", "pontos": 5, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 12, "criterio": "Conduta acolhedora", "pontos": 4, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 14, "criterio": "Script de encerramento completo", "pontos": 15, "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 15, "criterio": "Orientou sobre pesquisa", "pontos": 6, "resposta": "sim/não", "justificativa": "..."}}
  ],
  "criterios_eliminatorios": [
    {{"criterio": "Ofereceu serviço sem direito?", "ocorreu": false, "justificativa": "..."}},
    {{"criterio": "Preencheu veículo/peça incorretos?", "ocorreu": false, "justificativa": "..."}},
    {{"criterio": "Agiu de forma rude?", "ocorreu": false, "justificativa": "..."}},
    {{"criterio": "Encerrou/transferiu sem conhecimento?", "ocorreu": false, "justificativa": "..."}},
    {{"criterio": "Falou negativamente da empresa?", "ocorreu": false, "justificativa": "..."}},
    {{"criterio": "Forneceu informações incorretas?", "ocorreu": false, "justificativa": "..."}},
    {{"criterio": "Comentou sobre serviços externos?", "ocorreu": false, "justificativa": "..."}}
  ],
  "uso_script": {{"status": "completo/parcial/não utilizado", "justificativa": "..."}},
  "pontuacao_total": (calcular: soma APENAS grupos onde TODOS itens = sim),
  "resumo_geral": "..."
}}

CÁLCULO:
- Se itens 1,3,4,5,6 TODOS=sim → +26 pts
- Se itens 7,9,10 TODOS=sim → +30 pts
- Se itens 11,12 TODOS=sim → +9 pts
- Se itens 14,15 TODOS=sim → +21 pts
"""

        with st.spinner("Analisando a conversa..."):
            try:
                response = client.chat.completions.create(
                    model=modelo_gpt,
                    messages=[
                        {"role": "system", "content": "Você é um analista especializado em atendimento. Responda APENAS com JSON, sem texto adicional."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                result = response.choices[0].message.content.strip()

                with st.expander("Debug - Resposta bruta"):
                    st.code(result, language="json")
                
                try:
                    if not result.startswith("{"):
                        analysis = extract_json(result)
                    else:
                        analysis = json.loads(result)
                except Exception as json_error:
                    st.error(f"Erro ao processar JSON: {str(json_error)}")
                    st.text_area("Resposta da IA:", value=result, height=300)
                    st.stop()

                st.subheader("📋 Status Final")
                final = analysis.get("status_final", {})
                st.markdown(f"""
                <div class="status-box">
                <strong>Cliente:</strong> {final.get("satisfacao", "N/A")}<br>
                <strong>Desfecho:</strong> {final.get("desfecho", "N/A")}<br>
                <strong>Risco:</strong> {final.get("risco", "N/A")}
                </div>
                """, unsafe_allow_html=True)

                st.subheader("📝 Script de Encerramento")
                script_info = analysis.get("uso_script", {})
                script_status = script_info.get("status", "Não avaliado")
                script_class = get_script_status_class(script_status)
                
                st.markdown(f"""
                <div class="{script_class}">
                <strong>Status:</strong> {script_status}<br>
                <strong>Justificativa:</strong> {script_info.get("justificativa", "Não informado")}
                </div>
                """, unsafe_allow_html=True)

                st.subheader("⚠️ Critérios Eliminatórios")
                criterios_elim = analysis.get("criterios_eliminatorios", [])
                
                if criterios_elim:
                    criterios_violados = False
                    for criterio in criterios_elim:
                        if criterio.get("ocorreu", False):
                            criterios_violados = True
                            st.markdown(f"""
                            <div class="criterio-eliminatorio">
                            <strong>{criterio.get('criterio', 'N/A')}</strong><br>
                            {criterio.get('justificativa', '')}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    if not criterios_violados:
                        st.success("Nenhum critério eliminatório foi violado.")
                else:
                    st.info("Critérios eliminatórios não avaliados.")

                st.subheader("✅ Checklist Técnico (Avaliação por Grupos)")
                checklist = analysis.get("checklist", [])
                total = float(re.sub(r"[^\d.]", "", str(analysis.get("pontuacao_total", "0"))))
                progress_class = get_progress_class((total/86)*100)
                st.progress(min(total / 86, 1.0))
                st.markdown(f"<h3 class='{progress_class}'>{int(total)} pontos de 86 ({int((total/86)*100)}%)</h3>", unsafe_allow_html=True)

                with st.expander("Ver Detalhes do Checklist"):
                    for item in checklist:
                        resposta = item.get("resposta", "").lower()
                        classe = "criterio-sim" if resposta == "sim" else "criterio-nao"
                        icone = "✅" if resposta == "sim" else "❌"
                        
                        st.markdown(f"""
                        <div class="{classe}">
                        {icone} <strong>Item {item.get('item')}: {item.get('criterio')}</strong> ({item.get('pontos')} pts)<br>
                        <em>{item.get('justificativa')}</em>
                        </div>
                        """, unsafe_allow_html=True)

                st.subheader("📝 Resumo Geral")
                st.markdown(f"<div class='result-box'>{analysis.get('resumo_geral', 'N/A')}</div>", unsafe_allow_html=True)
                
                st.subheader("📄 Relatório em PDF")
                try:
                    pdf_bytes = create_pdf(analysis, transcript_text, modelo_gpt)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"MonitorAI_Relatorio_{timestamp}.pdf"
                    st.markdown(get_pdf_download_link(pdf_bytes, filename), unsafe_allow_html=True)
                except Exception as pdf_error:
                    st.error(f"Erro ao gerar PDF: {str(pdf_error)}")

            except Exception as e:
                st.error(f"Erro ao processar a análise: {str(e)}")
                try:
                    st.text_area("Resposta da IA:", value=response.choices[0].message.content.strip(), height=300)
                except:
                    st.text_area("Não foi possível recuperar a resposta da IA", height=300)
