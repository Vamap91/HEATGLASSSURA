import streamlit as st
# Configurações da página - DEVE ser a primeira chamada Streamlit
st.set_page_config(page_title="MonitorAI (PRD)", page_icon="🔴", layout="centered")

from openai import OpenAI
import tempfile
import re
import json
import base64
from datetime import datetime
from fpdf import FPDF

# Inicializa o cliente da OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Estrutura dos grupos de avaliação conforme o novo formulário
GRUPOS_AVALIACAO = {
    "Utilizou adequadamente as técnicas do atendimento?": {
        "peso_grupo": 26,
        "itens": [
            {"id": 1, "descricao": "Atendeu a ligação prontamente, dentro de 5 seg. e utilizou a saudação correta com as técnicas do atendimento encantador?", "peso": 10},
            {"id": 3, "descricao": "Confirmou os dados do cadastro e pediu 2 telefones para contato?", "peso": 6},
            {"id": 4, "descricao": "Verbalizou o script da LGPD?", "peso": 2},
            {"id": 5, "descricao": "Utilizou a técnica do eco para garantir o entendimento sobre as informações coletadas, evitando erros no processo e recontato do cliente?", "peso": 5},
            {"id": 6, "descricao": "Escutou atentamente a solicitação do segurado evitando solicitações em duplicidade?", "peso": 3}
        ]
    },
    "Adotou o procedimento de acordo com a rotina/transmitiu informações corretas e completas?": {
        "peso_grupo": 30,
        "itens": [
            {"id": 7, "descricao": "Compreendeu a solicitação do cliente em linha e demonstrou domínio sobre o produto/serviço?", "peso": 5},
            {"id": 9, "descricao": "Confirmou as informações completas sobre o dano no veículo?", "peso": 10},
            {"id": 10, "descricao": "Confirmou cidade para o atendimento e selecionou corretamente a primeira opção de loja identificada pelo sistema?", "peso": 10}
        ]
    },
    "Foi objetivo, contribuindo para redução do Tma?": {
        "peso_grupo": 9,
        "itens": [
            {"id": 11, "descricao": "A comunicação com o cliente foi eficaz: não houve uso de gírias, linguagem inadequada ou conversas paralelas? O analista informou quando ficou ausente da linha e quando retornou?", "peso": 5},
            {"id": 12, "descricao": "A conduta do analista foi acolhedora, com sorriso na voz, empatia e desejo verdadeiro em entender e solucionar a solicitação do cliente?", "peso": 4}
        ]
    },
    "Utilizou adequadamente o sistema e efetuou os registros de maneira correta e completa?": {
        "peso_grupo": 21,
        "itens": [
            {"id": 14, "descricao": "Realizou o script de encerramento completo, informando: prazo de validade, franquia, link de acompanhamento e vistoria, e orientou que o cliente aguarde o contato para agendamento?", "peso": 15},
            {"id": 15, "descricao": "Orientou o cliente sobre a pesquisa de satisfação do atendimento?", "peso": 6}
        ]
    }
}

# Função para criar PDF
def create_pdf(analysis, transcript_text, model_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Configurações de fonte
    pdf.set_font("Arial", "B", 16)
    
    # Cabeçalho
    pdf.set_fill_color(193, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "MonitorAI - Relatorio de Atendimento", 1, 1, "C", True)
    pdf.ln(5)
    
    # Informações gerais
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Data da analise: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
    pdf.cell(0, 10, f"Modelo utilizado: {model_name}", 0, 1)
    pdf.ln(5)
    
    # Pontuação Total
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Pontuacao Total", 0, 1)
    pontuacao = analysis.get("pontuacao_total", {})
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"{pontuacao.get('obtida', 0)} de {pontuacao.get('maxima', 86)} pontos ({pontuacao.get('percentual', 0)}%)", 0, 1)
    pdf.ln(5)
    
    # Avaliação por Grupos
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Avaliacao por Grupos", 0, 1)
    pdf.ln(3)
    
    grupos = analysis.get("grupos", [])
    for grupo in grupos:
        pdf.set_font("Arial", "B", 11)
        status = "[OK]" if grupo.get("aprovado") else "[FALHOU]"
        pdf.multi_cell(0, 8, f"{status} {grupo.get('nome')}")
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Pontos: {grupo.get('pontos_obtidos')} de {grupo.get('peso_grupo')}", 0, 1)
        
        # Itens do grupo
        for item in grupo.get("itens", []):
            status = "[OK]" if item.get("atendido") else "[X]"
            pdf.set_font("Arial", "", 9)
            descricao = item.get('descricao', '')[:80] + "..." if len(item.get('descricao', '')) > 80 else item.get('descricao', '')
            pdf.multi_cell(0, 6, f"  {status} Item {item.get('id')}: {descricao}")
            pdf.set_font("Arial", "I", 8)
            justificativa = item.get('justificativa', '')[:100]
            pdf.multi_cell(0, 5, f"       {justificativa}")
        
        pdf.ln(3)
    
    # Resumo Geral
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Resumo Geral", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, analysis.get("resumo_geral", "N/A"))
    pdf.ln(5)
    
    # Pontos Positivos
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Pontos Positivos", 0, 1)
    pdf.set_font("Arial", "", 10)
    for ponto in analysis.get("pontos_positivos", []):
        pdf.multi_cell(0, 6, f"+ {ponto}")
    pdf.ln(3)
    
    # Pontos de Melhoria
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Pontos de Melhoria", 0, 1)
    pdf.set_font("Arial", "", 10)
    for ponto in analysis.get("pontos_melhoria", []):
        pdf.multi_cell(0, 6, f"- {ponto}")
    pdf.ln(5)
    
    # Transcrição
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Transcricao da Ligacao", 0, 1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, transcript_text)
    
    return pdf.output(dest="S").encode("latin1")

# Função para criar link de download do PDF
def get_pdf_download_link(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Baixar Relatório em PDF</a>'
    return href

# Função para extrair JSON válido da resposta
def extract_json(text):
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except:
            pass
    
    raise ValueError(f"Não foi possível extrair JSON válido da resposta")

# Estilo visual
st.markdown("""
<style>
h1, h2, h3 {
    color: #C10000 !important;
}
.result-box {
    background-color: #ffecec;
    padding: 1em;
    border-left: 5px solid #C10000;
    border-radius: 6px;
    font-size: 1rem;
    white-space: pre-wrap;
    line-height: 1.5;
}
.stButton>button {
    background-color: #C10000;
    color: white;
    font-weight: 500;
    border-radius: 6px;
    padding: 0.4em 1em;
    border: none;
}
.status-box {
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    background-color: #ffecec;
    border: 1px solid #C10000;
}
.grupo-box {
    background-color: #ffffff;
    padding: 1.5em;
    border-radius: 10px;
    margin-bottom: 1.5em;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-left: 6px solid #C10000;
}
.grupo-aprovado {
    border-left-color: #00C100 !important;
    background-color: #f0fff0;
}
.grupo-reprovado {
    border-left-color: #FF0000 !important;
    background-color: #fff0f0;
}
.item-box {
    background-color: #f9f9f9;
    padding: 0.8em;
    margin: 0.5em 0;
    border-radius: 6px;
    border-left: 3px solid #ddd;
}
.item-ok {
    border-left-color: #00C100;
    background-color: #e6ffe6;
}
.item-falha {
    border-left-color: #FF0000;
    background-color: #ffecec;
}
.progress-high {
    color: #00C100;
}
.progress-medium {
    color: #FFD700;
}
.progress-low {
    color: #FF0000;
}
</style>
""", unsafe_allow_html=True)

# Função para determinar classe de progresso
def get_progress_class(value):
    if value >= 70:
        return "progress-high"
    elif value >= 50:
        return "progress-medium"
    else:
        return "progress-low"

# Modelo fixo
modelo_gpt = "gpt-4-turbo"

# Título
st.title("MonitorAI")
st.write("Análise inteligente de ligações: avaliação de atendimento ao cliente e conformidade com processos.")

# Upload de áudio
uploaded_file = st.file_uploader("Envie o áudio da ligação (.mp3)", type=["mp3"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.audio(uploaded_file, format='audio/mp3')

    if st.button("🔍 Analisar Atendimento"):
        # Transcrição via Whisper
        with st.spinner("Transcrevendo o áudio..."):
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            transcript_text = transcript.text

        with st.expander("Ver transcrição completa"):
            st.code(transcript_text, language="markdown")

        # Prompt com todas as instruções originais + lógica de grupos
        prompt = f"""
Você é um especialista em atendimento ao cliente da Carglass. Avalie a transcrição usando a estrutura de GRUPOS.

TRANSCRIÇÃO:
\"\"\"{transcript_text}\"\"\"

ESTRUTURA DE AVALIAÇÃO POR GRUPOS:

REGRA CRÍTICA: Se qualquer item dentro de um grupo falhar, TODO O GRUPO recebe 0 pontos.

**GRUPO 1: Utilizou adequadamente as técnicas do atendimento? (26 pontos)**
- Item 1 (10 pts): Atendeu a ligação prontamente, dentro de 5 seg. e utilizou a saudação correta com as técnicas do atendimento encantador?
- Item 3 (6 pts): Confirmou os dados do cadastro e pediu 2 telefones para contato?
- Item 4 (2 pts): Verbalizou o script da LGPD?
- Item 5 (5 pts): Utilizou a técnica do eco para garantir o entendimento sobre as informações coletadas?
- Item 6 (3 pts): Escutou atentamente a solicitação do segurado evitando solicitações em duplicidade?

**GRUPO 2: Adotou o procedimento de acordo com a rotina/transmitiu informações corretas e completas? (30 pontos)**
- Item 7 (5 pts): Compreendeu a solicitação do cliente em linha e demonstrou domínio sobre o produto/serviço?
- Item 9 (10 pts): Confirmou as informações completas sobre o dano no veículo?
- Item 10 (10 pts): Confirmou cidade para o atendimento e selecionou corretamente a primeira opção de loja?

**GRUPO 3: Foi objetivo, contribuindo para redução do Tma? (9 pontos)**
- Item 11 (5 pts): A comunicação foi eficaz: sem gírias, linguagem inadequada ou conversas paralelas?
- Item 12 (4 pts): A conduta foi acolhedora, com sorriso na voz, empatia e desejo verdadeiro?

**GRUPO 4: Utilizou adequadamente o sistema e efetuou os registros? (21 pontos)**
- Item 14 (15 pts): Realizou o script de encerramento completo?
- Item 15 (6 pts): Orientou o cliente sobre a pesquisa de satisfação?

INSTRUÇÕES DETALHADAS:

1. TÉCNICA DO ECO (Item 5): Marque SIM se:
   - Fez soletração fonética (ex: "R de rato, W de Washington")
   - Repetiu 2+ informações principais (placa, telefone, CPF)
   - Repetiu últimos 3+ dígitos de telefone/CPF
   - Repetiu com tom interrogativo E cliente confirmou

2. SCRIPT LGPD (Item 4): Deve mencionar compartilhamento de telefone com prestador. Variações válidas:
   - "Você permite compartilhar seu telefone com o prestador?"
   - "Podemos informar seu telefone ao prestador?"
   - "Você autoriza notificações no WhatsApp?"

3. SOLICITAÇÃO DE DADOS (Item 3): Deve solicitar TODOS os 6 dados:
   - Nome, CPF, Placa, Endereço, Telefone principal, Telefone secundário
   - EXCEÇÃO Bradesco/Sura/ALD: CPF e endereço dispensados se já no sistema
   - Cliente se identificar espontaneamente NÃO conta

4. CONFIRMAÇÃO DE DANOS (Item 9): Deve confirmar data, motivo, tamanho da trinca, LED/Xenon, dano na pintura

5. SCRIPT ENCERRAMENTO (Item 14): Deve incluir: validade, franquia, links WhatsApp, aguardar contato

REGRAS DE PONTUAÇÃO:
- Se TODOS itens do grupo = true → grupo recebe pontos totais
- Se QUALQUER item = false → grupo recebe 0 pontos
- Pontuação final = soma dos grupos aprovados

Retorne APENAS JSON:

{{
  "grupos": [
    {{
      "nome": "Utilizou adequadamente as técnicas do atendimento?",
      "peso_grupo": 26,
      "aprovado": true/false,
      "pontos_obtidos": 26 ou 0,
      "itens": [
        {{
          "id": 1,
          "descricao": "Atendeu a ligação prontamente...",
          "peso": 10,
          "atendido": true/false,
          "pontos_obtidos": 10 ou 0,
          "justificativa": "Explicação com evidências da transcrição"
        }}
      ]
    }}
  ],
  "pontuacao_total": {{
    "obtida": 0-86,
    "maxima": 86,
    "percentual": 0-100
  }},
  "resumo_geral": "Análise geral focando grupos aprovados/reprovados",
  "pontos_positivos": ["lista de pontos fortes"],
  "pontos_melhoria": ["lista de melhorias necessárias"]
}}

IMPORTANTE: Seja rigoroso. Um item não atendido reprova todo o grupo!
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

                # Debug
                with st.expander("Debug - Resposta bruta"):
                    st.code(result, language="json")
                
                # Parse JSON
                try:
                    if not result.startswith("{"):
                        analysis = extract_json(result)
                    else:
                        analysis = json.loads(result)
                except Exception as json_error:
                    st.error(f"Erro ao processar JSON: {str(json_error)}")
                    st.text_area("Resposta da IA:", value=result, height=300)
                    st.stop()

                # Pontuação Total
                st.subheader("📊 Pontuação Total")
                pontuacao = analysis.get("pontuacao_total", {})
                obtida = pontuacao.get("obtida", 0)
                maxima = pontuacao.get("maxima", 86)
                percentual = pontuacao.get("percentual", 0)
                
                progress_class = get_progress_class(percentual)
                st.progress(obtida / maxima)
                st.markdown(f"<h2 class='{progress_class}'>{int(obtida)} pontos de {maxima} ({percentual}%)</h2>", unsafe_allow_html=True)

                # Exibir Grupos
                st.subheader("📋 Avaliação por Grupos")
                
                grupos = analysis.get("grupos", [])
                for grupo in grupos:
                    aprovado = grupo.get("aprovado", False)
                    classe = "grupo-aprovado" if aprovado else "grupo-reprovado"
                    emoji = "✅" if aprovado else "❌"
                    
                    st.markdown(f"""
                    <div class="grupo-box {classe}">
                        <h3>{emoji} {grupo.get('nome')}</h3>
                        <p><strong>Pontuação:</strong> {grupo.get('pontos_obtidos')} de {grupo.get('peso_grupo')} pontos</p>
                        <p><strong>Status:</strong> {'APROVADO - Todos os itens atendidos' if aprovado else 'REPROVADO - Um ou mais itens não atendidos'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Itens do grupo
                    with st.expander(f"Ver Detalhes dos Itens"):
                        for item in grupo.get("itens", []):
                            atendido = item.get("atendido", False)
                            classe_item = "item-ok" if atendido else "item-falha"
                            emoji_item = "✅" if atendido else "❌"
                            
                            st.markdown(f"""
                            <div class="item-box {classe_item}">
                                <p><strong>{emoji_item} Item {item.get('id')}</strong> ({item.get('pontos_obtidos')}/{item.get('peso')} pontos)</p>
                                <p><em>{item.get('descricao')}</em></p>
                                <p><strong>Justificativa:</strong> {item.get('justificativa')}</p>
                            </div>
                            """, unsafe_allow_html=True)

                # Resumo Geral
                st.subheader("📝 Resumo Geral")
                st.markdown(f"<div class='result-box'>{analysis.get('resumo_geral', 'Não disponível')}</div>", unsafe_allow_html=True)

                # Pontos Positivos e Melhorias
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### ✨ Pontos Positivos")
                    for ponto in analysis.get("pontos_positivos", []):
                        st.markdown(f"- ✅ {ponto}")
                
                with col2:
                    st.markdown("#### 🎯 Pontos de Melhoria")
                    for ponto in analysis.get("pontos_melhoria", []):
                        st.markdown(f"- 🔸 {ponto}")
                
                # Gerar PDF
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
