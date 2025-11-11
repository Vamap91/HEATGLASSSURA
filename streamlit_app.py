import streamlit as st
st.set_page_config(page_title="MonitorAI - Análise por Grupos", page_icon="🔴", layout="centered")

from openai import OpenAI
import tempfile
import re
import json
import base64
from datetime import datetime
from fpdf import FPDF

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def clean_text_for_pdf(text):
    """Remove ou substitui caracteres que não são suportados pelo latin-1"""
    if not text:
        return ""
    # Substituições comuns
    replacements = {
        '\u2026': '...',  # Reticências
        '\u2013': '-',    # En dash
        '\u2014': '--',   # Em dash
        '\u2018': "'",    # Left single quote
        '\u2019': "'",    # Right single quote
        '\u201C': '"',    # Left double quote
        '\u201D': '"',    # Right double quote
        '\u2022': '*',    # Bullet
        '\u2032': "'",    # Prime
        '\u2033': '"',    # Double prime
        '\u00B0': ' graus',  # Degree symbol
        '\u00A9': '(c)',  # Copyright
        '\u00AE': '(R)',  # Registered
        '\u2122': '(TM)', # Trademark
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    
    # Remove qualquer caractere que não seja latin-1
    try:
        text.encode('latin-1')
    except UnicodeEncodeError:
        # Se ainda há caracteres problemáticos, remove-os
        text = text.encode('latin-1', errors='ignore').decode('latin-1')
    
    return text

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
    
    # Status Final
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Status Final", 0, 1)
    pdf.set_font("Arial", "", 12)
    final = analysis.get("status_final", {})
    pdf.cell(0, 10, clean_text_for_pdf(f"Satisfacao: {final.get('satisfacao', 'N/A')}"), 0, 1)
    pdf.cell(0, 10, clean_text_for_pdf(f"Desfecho: {final.get('desfecho', 'N/A')}"), 0, 1)
    pdf.cell(0, 10, clean_text_for_pdf(f"Risco: {final.get('risco', 'N/A')}"), 0, 1)
    pdf.ln(5)
    
    # Pontuação Total
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Pontuacao Total", 0, 1)
    pdf.set_font("Arial", "B", 12)
    total = clean_text_for_pdf(str(analysis.get("pontuacao_total_percentual", "N/A")))
    pdf.cell(0, 10, f"{total}% (avaliacao por grupos)", 0, 1)
    pdf.ln(5)
    
    # Avaliação por Grupos
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Avaliacao por Grupos", 0, 1)
    pdf.ln(3)
    
    grupos = analysis.get("grupos_avaliacao", [])
    for grupo in grupos:
        feito = grupo.get('feito')
        if feito is None:
            continue  # Pular não avaliados
        
        status_text = "TOTALMENTE CERTO" if feito else "TOTALMENTE INCORRETO"
        
        pdf.set_font("Arial", "B", 12)
        nome_grupo = clean_text_for_pdf(grupo.get('nome', ''))
        percentual = grupo.get('percentual', 0)
        pdf.multi_cell(0, 8, f"{nome_grupo} ({percentual}%) - {status_text}")
        pdf.set_font("Arial", "", 10)
        justificativa = clean_text_for_pdf(grupo.get('justificativa', 'N/A'))
        pdf.multi_cell(0, 6, f"Justificativa: {justificativa}")
        pdf.ln(3)
    
    # Resumo Geral
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Resumo Geral", 0, 1)
    pdf.set_font("Arial", "", 12)
    resumo = clean_text_for_pdf(analysis.get("resumo_geral", "N/A"))
    pdf.multi_cell(0, 10, resumo)
    pdf.ln(5)
    
    # Critérios Eliminatórios
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Criterios Eliminatorios", 0, 1)
    pdf.ln(3)
    criterios_elim = analysis.get("criterios_eliminatorios", [])
    for criterio in criterios_elim:
        if criterio.get("ocorreu", False):
            pdf.set_font("Arial", "B", 11)
            criterio_texto = clean_text_for_pdf(criterio.get('criterio', 'N/A'))
            pdf.multi_cell(0, 8, f"VIOLADO: {criterio_texto}")
            pdf.set_font("Arial", "", 10)
            justificativa = clean_text_for_pdf(criterio.get('justificativa', ''))
            pdf.multi_cell(0, 6, justificativa)
            pdf.ln(3)
    
    # Detalhamento Técnico
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Detalhamento Tecnico por Item", 0, 1)
    pdf.ln(5)
    
    checklist = analysis.get("checklist_detalhado", [])
    for item in checklist:
        pdf.set_font("Arial", "B", 11)
        criterio = clean_text_for_pdf(item.get('criterio', ''))
        pdf.multi_cell(0, 8, f"Item {item.get('item')}: {criterio}")
        pdf.set_font("Arial", "", 10)
        resposta = clean_text_for_pdf(item.get('resposta', ''))
        pdf.cell(0, 6, f"Resposta: {resposta}", 0, 1)
        justificativa = clean_text_for_pdf(item.get('justificativa', ''))
        pdf.multi_cell(0, 6, f"Justificativa: {justificativa}")
        pdf.ln(3)
    
    # Transcrição
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Transcricao", 0, 1)
    pdf.set_font("Arial", "", 10)
    transcript_clean = clean_text_for_pdf(transcript_text)
    pdf.multi_cell(0, 10, transcript_clean)
    
    return pdf.output(dest="S").encode("latin1")

def get_pdf_download_link(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📥 Baixar Relatório em PDF</a>'

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
.grupo-feito { background-color: #e6ffe6; padding: 15px; border-left: 5px solid #00C100; border-radius: 6px; margin-bottom: 10px; }
.grupo-nao-feito { background-color: #ffcccc; padding: 15px; border-left: 5px solid #FF0000; border-radius: 6px; margin-bottom: 10px; }
.progress-high { color: #00C100; }
.progress-medium { color: #FFD700; }
.progress-low { color: #FF0000; }
.criterio-eliminatorio { background-color: #ffcccc; padding: 10px; border-radius: 6px; margin-top: 10px; border: 2px solid #FF0000; font-weight: bold; }
.item-detalhe { background-color: #f5f5f5; padding: 10px; border-radius: 4px; margin: 5px 0; border-left: 3px solid #666; }
</style>
""", unsafe_allow_html=True)

def get_progress_class(value):
    if value >= 70: return "progress-high"
    elif value >= 50: return "progress-medium"
    else: return "progress-low"

modelo_gpt = "gpt-4o"

st.title("MonitorAI SURA - Análise por Grupos")
st.write("Análise inteligente de ligações: avaliação estruturada por grupos de competências.")

uploaded_file = st.file_uploader("📁 Envie o áudio da ligação (.mp3)", type=["mp3"])

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

        with st.expander("📄 Ver transcrição completa"):
            st.code(transcript_text, language="markdown")

        prompt = f"""
Você é um especialista em atendimento ao cliente da Carglass. Avalie a transcrição usando o sistema de GRUPOS.

TRANSCRIÇÃO:
\"\"\"{transcript_text}\"\"\"

⚠️ LÓGICA DE AVALIAÇÃO POR GRUPOS - REGRA CRÍTICA:
Cada GRUPO só é considerado "FEITO" se TODOS os itens dentro dele receberem "sim".
Se QUALQUER item de um grupo receber "não", o GRUPO INTEIRO é marcado como "NÃO FEITO" e recebe 0%.

ESTRUTURA DE GRUPOS:

**GRUPO A (10%): Utilizou adequadamente as técnicas do atendimento?**
Itens que compõem este grupo:
- Item 1 (peso interno 10): Atendeu a ligação prontamente, dentro de 5 seg. e utilizou a saudação correta com as técnicas do atendimento encantador?
- Item 3 (peso interno 6): Confirmou os dados do cadastro e pediu 2 telefones para contato?
- Item 4 (peso interno 2): Verbalizou o script da LGPD?
- Item 5 (peso interno 5): Utilizou a técnica do eco para garantir o entendimento sobre as informações coletadas?

**GRUPO B (30%): Adotou o procedimento de acordo com a rotina/transmitiu informações corretas e completas?**
Itens que compõem este grupo:
- Item 6 (peso interno 3): Escutou atentamente a solicitação do segurado evitando solicitações em duplicidade?
- Item 7 (peso interno 5): Compreendeu a solicitação do cliente em linha e demonstrou domínio sobre o produto/serviço?
- Item 9 (peso interno 10): Confirmou as informações completas sobre o dano no veículo?
- Item 10 (peso interno 10): Confirmou cidade para o atendimento e selecionou corretamente a primeira opção de loja identificada pelo sistema?

**GRUPO C (10%): Foi objetivo, contribuindo para redução do TMA?**
Itens que compõem este grupo:
- Item 11 (peso interno 5): A comunicação com o cliente foi eficaz: não houve uso de gírias, linguagem inadequada ou conversas paralelas? O analista informou quando ficou ausente da linha e quando retornou?
- Item 12 (peso interno 4): A conduta do analista foi acolhedora, com sorriso na voz, empatia e desejo verdadeiro em entender e solucionar a solicitação do cliente?

**GRUPO D (20%): Utilizou adequadamente o sistema e efetuou os registros de maneira correta e completa?**
Itens que compõem este grupo:
- Item 14 (peso interno 15): Realizou o script de encerramento completo, informando: prazo de validade, franquia, link de acompanhamento e vistoria, e orientou que o cliente aguarde o contato para agendamento?
- Item 15 (peso interno 6): Orientou o cliente sobre a pesquisa de satisfação do atendimento?

**GRUPO E (10%): Transferiu a ligação ao superior quando solicitado e/ou necessário?**
REGRA ESPECIAL PARA GRUPO E:
- No modelo atual, colaboradores são incentivados a serem protagonistas do atendimento (autonomia)
- Buscam auxílio quando necessário, mas são responsáveis por concluir as solicitações
- Superiores monitoram e apoiam, mas NÃO assumem as chamadas

AVALIAÇÃO:
- Se NÃO transferiu/acionou superior = VERDE (Totalmente Certo) = +10% na pontuação
- Se transferiu/acionou superior = VERMELHO (Totalmente Incorreto) = 0% na pontuação

Marque "feito: true" se o atendente NÃO transferiu e resolveu com autonomia.
Marque "feito: false" se o atendente transferiu ou acionou o superior.

**GRUPO F (20%): Teve foco no cliente?**
Avalie o foco no cliente durante TODO o atendimento:
- Priorizou as necessidades do cliente?
- Manteve empatia e interesse genuíno?
- Buscou a melhor solução para o cliente?
- Demonstrou comprometimento em resolver o problema?
Este grupo conta 20% na pontuação total.

INSTRUÇÕES DETALHADAS PARA CADA ITEM:

**ITEM 5 - TÉCNICA DO ECO (AVALIAÇÃO RIGOROSA):**
Marque como "SIM" SE QUALQUER UMA das condições abaixo for atendida:

CONDIÇÃO A - SOLETRAÇÃO FONÉTICA (APROVAÇÃO AUTOMÁTICA):
- Soletração fonética de QUALQUER informação (placa, telefone, CPF)
- Exemplos: "R de rato, W de Washington", "rato, sapo, xícara", "A de avião, B de bola"
- Uma única soletração fonética é suficiente

CONDIÇÃO B - ECO MÚLTIPLO:
- Repetiu (completa ou parcialmente) PELO MENOS 2 informações: placa, telefone principal, CPF, telefone secundário

CONDIÇÃO C - ECO PARCIAL (APROVAÇÃO FLEXÍVEL):
- Repetiu parte significativa de uma informação principal
- Exemplos: "0800-703-0203" → "0203" (últimos dígitos)
- Eco parcial de 3+ dígitos finais é válido mesmo sem confirmação explícita

CONDIÇÃO D - ECO INTERROGATIVO CONFIRMADO:
- Repetiu informação com tom interrogativo E cliente confirmou
- Exemplos: "54-3381-5775?" → Cliente: "Isso"

NÃO É ECO VÁLIDO: Apenas "ok", "certo", "entendi" sem repetir informação

**ITEM 3 - SOLICITAÇÃO DE DADOS (AVALIAÇÃO RIGOROSA):**
Marque como "SIM" APENAS se o atendente solicitou EXPLICITAMENTE TODOS os 6 dados:
1. NOME do cliente
2. CPF do cliente
3. PLACA do veículo
4. ENDEREÇO do cliente
5. TELEFONE PRINCIPAL
6. TELEFONE SECUNDÁRIO

EXCEÇÃO BRADESCO/SURA/ALD: CPF e endereço podem ser dispensados APENAS se o atendente CONFIRMAR que já estão no sistema.

**ITEM 4 - SCRIPT LGPD:**
Válido se mencionar compartilhamento do telefone com prestador, com ênfase em privacidade/consentimento.
Variações aceitas:
- "Você permite que compartilhemos seu telefone com o prestador?"
- "Podemos informar seu telefone ao prestador que irá atender?"
- "Você autoriza o envio de notificações no WhatsApp?"

**ITEM 14 - SCRIPT DE ENCERRAMENTO:**
Deve incluir TODOS os elementos:
- Prazo de validade
- Franquia
- Link de acompanhamento e vistoria
- Orientação para aguardar contato para agendamento

**CRITÉRIOS ELIMINATÓRIOS:**
- Ofereceu serviço sem direito
- Preencheu veículo/peça incorretos
- Agiu com rudeza
- Encerrou/transferiu sem conhecimento do cliente
- Falou negativamente da empresa
- Forneceu informações incorretas ou fez suposições infundadas
- Comentou sobre serviços externos

RETORNE APENAS JSON (sem ``` ou texto adicional):

{{
  "status_final": {{
    "satisfacao": "satisfeito/insatisfeito/neutro",
    "risco": "baixo/médio/alto",
    "desfecho": "resolvido/pendente/não resolvido"
  }},
  "grupos_avaliacao": [
    {{
      "grupo": "A",
      "nome": "Utilizou adequadamente as técnicas do atendimento?",
      "percentual": 10,
      "feito": true/false,
      "justificativa": "Explicação detalhada considerando TODOS os itens (1, 3, 4, 5) do grupo"
    }},
    {{
      "grupo": "B",
      "nome": "Adotou o procedimento de acordo com a rotina/transmitiu informações corretas e completas?",
      "percentual": 30,
      "feito": true/false,
      "justificativa": "Explicação detalhada considerando TODOS os itens (6, 7, 9, 10) do grupo"
    }},
    {{
      "grupo": "C",
      "nome": "Foi objetivo, contribuindo para redução do TMA?",
      "percentual": 10,
      "feito": true/false,
      "justificativa": "Explicação detalhada considerando TODOS os itens (11, 12) do grupo"
    }},
    {{
      "grupo": "D",
      "nome": "Utilizou adequadamente o sistema e efetuou os registros de maneira correta e completa?",
      "percentual": 20,
      "feito": true/false,
      "justificativa": "Explicação detalhada considerando TODOS os itens (14, 15) do grupo"
    }},
    {{
      "grupo": "E",
      "nome": "Transferiu a ligação ao superior quando solicitado e/ou necessário?",
      "percentual": 10,
      "feito": true/false,
      "justificativa": "Se NÃO transferiu (autonomia) = true (+10%). Se transferiu = false (0%). Explicar se houve transferência ou se resolveu com autonomia."
    }},
    {{
      "grupo": "F",
      "nome": "Teve foco no cliente?",
      "percentual": 20,
      "feito": true/false,
      "justificativa": "Análise detalhada do foco no cliente durante TODO o atendimento: priorizou necessidades, manteve empatia, buscou melhor solução, demonstrou comprometimento"
    }}
  ],
  "checklist_detalhado": [
    {{"item": 1, "grupo": "A", "criterio": "Atendeu prontamente e usou saudação correta", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 3, "grupo": "A", "criterio": "Confirmou cadastro e pediu 2 telefones", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 4, "grupo": "A", "criterio": "Verbalizou script LGPD", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 5, "grupo": "A", "criterio": "Utilizou técnica do eco", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 6, "grupo": "B", "criterio": "Escutou atentamente", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 7, "grupo": "B", "criterio": "Demonstrou domínio", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 9, "grupo": "B", "criterio": "Confirmou danos no veículo", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 10, "grupo": "B", "criterio": "Confirmou cidade", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 11, "grupo": "C", "criterio": "Comunicação eficaz", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 12, "grupo": "C", "criterio": "Conduta acolhedora", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 14, "grupo": "D", "criterio": "Script encerramento completo", "resposta": "sim/não", "justificativa": "..."}},
    {{"item": 15, "grupo": "D", "criterio": "Orientou sobre pesquisa", "resposta": "sim/não", "justificativa": "..."}}
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
  "pontuacao_total_percentual": (soma dos percentuais dos grupos onde feito=true),
  "resumo_geral": "Resumo executivo do atendimento, destacando pontos fortes e áreas de melhoria"
}}

CÁLCULO DA PONTUAÇÃO:
- Some APENAS os percentuais dos grupos onde TODOS os itens = "sim" (feito=true)
- Exemplo: Se grupos A, C, E e F estão completos → 10% + 10% + 10% + 20% = 50%
- IMPORTANTE: Grupo E vale 10% SE o atendente NÃO transferiu (demonstrou autonomia)
- Pontuação máxima possível: 100%
"""

        with st.spinner("Analisando a conversa por grupos..."):
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

                with st.expander("🔧 Debug - Resposta bruta"):
                    st.code(result, language="json")
                
                try:
                    if not result.startswith("{"):
                        analysis = extract_json(result)
                    else:
                        analysis = json.loads(result)
                except Exception as json_error:
                    st.error(f"❌ Erro ao processar JSON: {str(json_error)}")
                    st.text_area("Resposta da IA:", value=result, height=300)
                    st.stop()

                # Status Final
                st.subheader("📊 Status Final do Atendimento")
                final = analysis.get("status_final", {})
                st.markdown(f"""
                <div class="status-box">
                <strong>Satisfação do Cliente:</strong> {final.get("satisfacao", "N/A")}<br>
                <strong>Desfecho:</strong> {final.get("desfecho", "N/A")}<br>
                <strong>Nível de Risco:</strong> {final.get("risco", "N/A")}
                </div>
                """, unsafe_allow_html=True)

                # Pontuação Total
                total_percentual = analysis.get("pontuacao_total_percentual", 0)
                progress_class = get_progress_class(total_percentual)
                st.subheader("📈 Pontuação Total")
                st.progress(min(total_percentual / 100, 1.0))
                st.markdown(f"<h2 class='{progress_class}'>{total_percentual}% de 100%</h2>", unsafe_allow_html=True)

                # Avaliação por Grupos (Principal)
                st.subheader("✅ Avaliação por Grupos")
                st.write("*Cada grupo só é considerado TOTALMENTE CERTO se TODOS os seus itens forem aprovados*")
                
                grupos = analysis.get("grupos_avaliacao", [])
                for grupo in grupos:
                    feito = grupo.get("feito")
                    grupo_letra = grupo.get("grupo", "")
                    percentual = grupo.get("percentual", 0)
                    
                    # Pular se não foi avaliado
                    if feito is None:
                        continue
                    
                    # Todos os grupos agora contam para pontuação (A, B, C, D, E, F = 100%)
                    classe = "grupo-feito" if feito else "grupo-nao-feito"
                    icone = "✅ TOTALMENTE CERTO" if feito else "❌ TOTALMENTE INCORRETO"
                    
                    st.markdown(f"""
                    <div class="{classe}">
                    <strong>{icone} | {grupo.get('nome')} ({percentual}%)</strong><br>
                    <em>{grupo.get('justificativa', 'N/A')}</em>
                    </div>
                    """, unsafe_allow_html=True)>
                    <strong>{icone} | {grupo.get('nome')} ({grupo.get('percentual')}%)</strong><br>
                    <em>{grupo.get('justificativa', 'N/A')}</em>
                    </div>
                    """, unsafe_allow_html=True)

                # Critérios Eliminatórios
                st.subheader("⚠️ Critérios Eliminatórios")
                criterios_elim = analysis.get("criterios_eliminatorios", [])
                
                if criterios_elim:
                    criterios_violados = False
                    for criterio in criterios_elim:
                        if criterio.get("ocorreu", False):
                            criterios_violados = True
                            st.markdown(f"""
                            <div class="criterio-eliminatorio">
                            <strong>⛔ {criterio.get('criterio', 'N/A')}</strong><br>
                            {criterio.get('justificativa', '')}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    if not criterios_violados:
                        st.success("✅ Nenhum critério eliminatório foi violado.")
                else:
                    st.info("ℹ️ Critérios eliminatórios não avaliados.")

                # Detalhamento Técnico (Expandível)
                with st.expander("🔍 Ver Detalhamento Técnico por Item"):
                    st.write("*Avaliação individual de cada item que compõe os grupos*")
                    checklist = analysis.get("checklist_detalhado", [])
                    
                    # Agrupar por grupo
                    grupos_dict = {}
                    for item in checklist:
                        grupo = item.get("grupo", "")
                        if grupo not in grupos_dict:
                            grupos_dict[grupo] = []
                        grupos_dict[grupo].append(item)
                    
                    for grupo_letra in sorted(grupos_dict.keys()):
                        st.markdown(f"**📌 Grupo {grupo_letra}**")
                        for item in grupos_dict[grupo_letra]:
                            resposta = item.get("resposta", "").lower()
                            icone = "✅" if resposta == "sim" else "❌"
                            
                            st.markdown(f"""
                            <div class="item-detalhe">
                            {icone} <strong>Item {item.get('item')}: {item.get('criterio')}</strong><br>
                            <em>{item.get('justificativa')}</em>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("---")

                # Resumo Geral
                st.subheader("📝 Resumo Geral")
                st.markdown(f"<div class='result-box'>{analysis.get('resumo_geral', 'N/A')}</div>", unsafe_allow_html=True)
                
                # PDF
                st.subheader("📄 Relatório em PDF")
                try:
                    pdf_bytes = create_pdf(analysis, transcript_text, modelo_gpt)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"MonitorAI_Grupos_{timestamp}.pdf"
                    st.markdown(get_pdf_download_link(pdf_bytes, filename), unsafe_allow_html=True)
                except Exception as pdf_error:
                    st.error(f"❌ Erro ao gerar PDF: {str(pdf_error)}")

            except Exception as e:
                st.error(f"❌ Erro ao processar a análise: {str(e)}")
                try:
                    st.text_area("Resposta da IA:", value=response.choices[0].message.content.strip(), height=300)
                except:
                    st.text_area("Não foi possível recuperar a resposta da IA", height=300)
