import streamlit as st
# Configurações da página - DEVE ser a primeira chamada Streamlit
st.set_page_config(page_title="MonitorAI Carglass - Análise por Grupos", page_icon="🔴", layout="wide")

from openai import OpenAI
import tempfile
import re
import json
import base64
from datetime import datetime
from fpdf import FPDF

# Inicializa o novo cliente da OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Estrutura dos grupos de avaliação conforme o formulário
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

# Função para criar PDF com nova estrutura
def create_pdf(analysis, transcript_text, model_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Configurações de fonte
    pdf.set_font("Arial", "B", 16)
    
    # Cabeçalho
    pdf.set_fill_color(193, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "MonitorAI Carglass - Relatorio de Monitoria", 1, 1, "C", True)
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
    pdf.cell(0, 10, f"{pontuacao.get('obtida', 0)} de {pontuacao.get('maxima', 86)} pontos", 0, 1)
    pdf.cell(0, 10, f"Percentual: {pontuacao.get('percentual', 0)}%", 0, 1)
    pdf.ln(5)
    
    # Resultado dos Grupos
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Avaliacao por Grupos", 0, 1)
    pdf.ln(3)
    
    grupos = analysis.get("grupos", [])
    for grupo in grupos:
        pdf.set_font("Arial", "B", 11)
        status_emoji = "OK" if grupo.get("aprovado") else "FALHOU"
        pdf.multi_cell(0, 8, f"[{status_emoji}] {grupo.get('nome')}")
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Pontos: {grupo.get('pontos_obtidos')} de {grupo.get('peso_grupo')}", 0, 1)
        
        # Itens do grupo
        for item in grupo.get("itens", []):
            status = "OK" if item.get("atendido") else "X"
            pdf.set_font("Arial", "", 9)
            pdf.multi_cell(0, 6, f"  [{status}] Item {item.get('id')}: {item.get('descricao')[:80]}...")
            pdf.cell(0, 5, f"       Pontos: {item.get('pontos_obtidos')}/{item.get('peso')} - {item.get('justificativa')[:60]}", 0, 1)
        
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
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📥 Baixar Relatório Completo em PDF</a>'
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
    
    raise ValueError(f"Não foi possível extrair JSON válido da resposta: {text[:100]}...")

# Estilo visual aprimorado
st.markdown("""
<style>
h1, h2, h3 {
    color: #C10000 !important;
}
.main-header {
    background: linear-gradient(135deg, #C10000 0%, #8B0000 100%);
    padding: 2em;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 2em;
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
.pontuacao-box {
    background: linear-gradient(135deg, #C10000 0%, #8B0000 100%);
    color: white;
    padding: 2em;
    border-radius: 10px;
    text-align: center;
    margin: 2em 0;
}
.pontuacao-numero {
    font-size: 3em;
    font-weight: bold;
}
.resumo-box {
    background-color: #ffecec;
    padding: 1.5em;
    border-left: 5px solid #C10000;
    border-radius: 8px;
    margin: 1em 0;
}
.stButton>button {
    background-color: #C10000;
    color: white;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.6em 2em;
    border: none;
    font-size: 1.1em;
}
.stButton>button:hover {
    background-color: #8B0000;
}
</style>
""", unsafe_allow_html=True)

# Cabeçalho
st.markdown("""
<div class="main-header">
    <h1>🔴 MonitorAI Carglass</h1>
    <p style="font-size: 1.2em; margin-top: 0.5em;">Sistema de Análise de Atendimento por Grupos</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://www.carglass.com.br/themes/custom/carglass/logo.svg", width=200)
    st.markdown("---")
    st.markdown("### ⚙️ Configurações")
    
    modelo_gpt = st.selectbox(
        "Modelo GPT:",
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 📊 Estrutura de Avaliação")
    st.markdown("""
    **4 Grupos Principais:**
    1. Técnicas de atendimento (26 pts)
    2. Procedimentos e informações (30 pts)
    3. Objetividade e redução de TMA (9 pts)
    4. Sistema e registros (21 pts)
    
    **Total: 86 pontos**
    
    ⚠️ Se um item falhar, todo o grupo falha!
    """)

# Upload de áudio
st.markdown("### 🎤 Upload do Áudio do Atendimento")
audio_file = st.file_uploader("Selecione o arquivo de áudio (.mp3, .wav, .m4a)", type=["mp3", "wav", "m4a"])

if audio_file:
    st.audio(audio_file)
    
    if st.button("🚀 Iniciar Análise Completa", use_container_width=True):
        # Transcrição
        st.markdown("### 📝 Etapa 1: Transcrição do Áudio")
        with st.spinner("Transcrevendo o áudio..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(audio_file.getvalue())
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language="pt"
                )
            
            transcript_text = transcript.text
            st.success("✅ Transcrição concluída!")
            
            with st.expander("📄 Ver Transcrição Completa"):
                st.text_area("Transcrição:", value=transcript_text, height=200)
        
        # Análise com o novo prompt
        st.markdown("### 🔍 Etapa 2: Análise por Grupos")
        
        # Construir o prompt detalhado
        prompt = f"""Analise a seguinte transcrição de atendimento da Carglass e avalie cada item dentro dos grupos definidos.

TRANSCRIÇÃO:
{transcript_text}

IMPORTANTE: A avaliação é feita por GRUPOS. Se qualquer item dentro de um grupo falhar (não for atendido), TODO O GRUPO recebe 0 pontos.

ESTRUTURA DE AVALIAÇÃO POR GRUPOS:

**GRUPO 1: Utilizou adequadamente as técnicas do atendimento? (26 pontos)**
- Item 1 (10 pts): Atendeu a ligação prontamente, dentro de 5 seg. e utilizou a saudação correta com as técnicas do atendimento encantador?
- Item 3 (6 pts): Confirmou os dados do cadastro e pediu 2 telefones para contato?
- Item 4 (2 pts): Verbalizou o script da LGPD?
- Item 5 (5 pts): Utilizou a técnica do eco para garantir o entendimento sobre as informações coletadas, evitando erros no processo e recontato do cliente?
- Item 6 (3 pts): Escutou atentamente a solicitação do segurado evitando solicitações em duplicidade?

**GRUPO 2: Adotou o procedimento de acordo com a rotina/transmitiu informações corretas e completas? (30 pontos)**
- Item 7 (5 pts): Compreendeu a solicitação do cliente em linha e demonstrou domínio sobre o produto/serviço?
- Item 9 (10 pts): Confirmou as informações completas sobre o dano no veículo?
- Item 10 (10 pts): Confirmou cidade para o atendimento e selecionou corretamente a primeira opção de loja identificada pelo sistema?

**GRUPO 3: Foi objetivo, contribuindo para redução do Tma? (9 pontos)**
- Item 11 (5 pts): A comunicação com o cliente foi eficaz: não houve uso de gírias, linguagem inadequada ou conversas paralelas? O analista informou quando ficou ausente da linha e quando retornou?
- Item 12 (4 pts): A conduta do analista foi acolhedora, com sorriso na voz, empatia e desejo verdadeiro em entender e solucionar a solicitação do cliente?

**GRUPO 4: Utilizou adequadamente o sistema e efetuou os registros de maneira correta e completa? (21 pontos)**
- Item 14 (15 pts): Realizou o script de encerramento completo, informando: prazo de validade, franquia, link de acompanhamento e vistoria, e orientou que o cliente aguarde o contato para agendamento?
- Item 15 (6 pts): Orientou o cliente sobre a pesquisa de satisfação do atendimento?

REGRAS DE PONTUAÇÃO:
1. Avalie cada item individualmente (true/false)
2. Se TODOS os itens de um grupo forem atendidos (true), o grupo recebe a pontuação total
3. Se QUALQUER item de um grupo falhar (false), o grupo inteiro recebe 0 pontos
4. A pontuação final é a soma dos pontos de todos os grupos aprovados

Retorne APENAS um JSON válido com esta estrutura exata:

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
          "justificativa": "Explicação detalhada"
        }}
      ]
    }}
  ],
  "pontuacao_total": {{
    "obtida": 0-86,
    "maxima": 86,
    "percentual": 0-100
  }},
  "resumo_geral": "Análise geral do atendimento",
  "pontos_positivos": ["lista", "de", "pontos", "fortes"],
  "pontos_melhoria": ["lista", "de", "melhorias"]
}}

IMPORTANTE: Seja rigoroso na avaliação. Um único item não atendido reprova todo o grupo!
"""

        with st.spinner("Analisando o atendimento por grupos..."):
            try:
                response = client.chat.completions.create(
                    model=modelo_gpt,
                    messages=[
                        {"role": "system", "content": "Você é um analista especializado em qualidade de atendimento da Carglass. Responda APENAS com JSON válido, sem texto adicional."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                
                result = response.choices[0].message.content.strip()
                
                # Debug
                with st.expander("🔧 Debug - Resposta Bruta"):
                    st.code(result, language="json")
                
                # Parse JSON
                analysis = json.loads(result)
                
                # Exibir Pontuação Total
                st.markdown("---")
                pontuacao = analysis.get("pontuacao_total", {})
                obtida = pontuacao.get("obtida", 0)
                maxima = pontuacao.get("maxima", 86)
                percentual = pontuacao.get("percentual", 0)
                
                st.markdown(f"""
                <div class="pontuacao-box">
                    <div class="pontuacao-numero">{obtida} / {maxima}</div>
                    <div style="font-size: 1.5em; margin-top: 0.5em;">{percentual}% de aproveitamento</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Barra de progresso
                st.progress(obtida / maxima)
                
                # Exibir Grupos
                st.markdown("### 📊 Análise Detalhada por Grupos")
                
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
                    with st.expander(f"📋 Ver Detalhes dos Itens do Grupo"):
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
                st.markdown("### 📝 Resumo da Análise")
                st.markdown(f"""
                <div class="resumo-box">
                    {analysis.get('resumo_geral', 'Não disponível')}
                </div>
                """, unsafe_allow_html=True)
                
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
                st.markdown("---")
                st.markdown("### 📄 Relatório em PDF")
                try:
                    pdf_bytes = create_pdf(analysis, transcript_text, modelo_gpt)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"MonitorAI_Carglass_{timestamp}.pdf"
                    st.markdown(get_pdf_download_link(pdf_bytes, filename), unsafe_allow_html=True)
                except Exception as pdf_error:
                    st.error(f"Erro ao gerar PDF: {str(pdf_error)}")
                
            except Exception as e:
                st.error(f"❌ Erro ao processar a análise: {str(e)}")
                st.text_area("Detalhes do erro:", value=str(e), height=200)
else:
    st.info("👆 Faça upload de um arquivo de áudio para iniciar a análise")
    
    # Informações adicionais
    st.markdown("---")
    st.markdown("### ℹ️ Como funciona a análise")
    st.markdown("""
    1. **Upload**: Envie o áudio do atendimento
    2. **Transcrição**: O sistema converte áudio em texto usando Whisper
    3. **Análise por Grupos**: Cada grupo é avaliado separadamente
    4. **Critério de Aprovação**: TODOS os itens de um grupo devem ser atendidos
    5. **Pontuação**: Grupos aprovados somam pontos; grupos reprovados = 0 pontos
    6. **Relatório**: Gere um PDF completo com toda a análise
    """)
