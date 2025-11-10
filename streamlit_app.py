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

# Inicializa o novo cliente da OpenAI
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

# Função para criar PDF - ADAPTADA PARA GRUPOS
def create_pdf(analysis, transcript_text, model_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Configurações de fonte
    pdf.set_font("Arial", "B", 16)
    
    # Cabeçalho
    pdf.set_fill_color(193, 0, 0)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "MonitorAI - Relatorio de Atendimento Carglass", 1, 1, "C", True)
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
        status_emoji = "[OK]" if grupo.get("aprovado") else "[FALHOU]"
        pdf.multi_cell(0, 8, f"{status_emoji} {grupo.get('nome')}")
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Pontos: {grupo.get('pontos_obtidos')} de {grupo.get('peso_grupo')}", 0, 1)
        
        # Itens do grupo
        for item in grupo.get("itens", []):
            status = "[OK]" if item.get("atendido") else "[X]"
            pdf.set_font("Arial", "", 9)
            descricao_curta = item.get('descricao')[:80] + "..." if len(item.get('descricao', '')) > 80 else item.get('descricao', '')
            pdf.multi_cell(0, 6, f"  {status} Item {item.get('id')}: {descricao_curta}")
            pdf.set_font("Arial", "I", 8)
            justificativa_curta = item.get('justificativa', '')[:100]
            pdf.multi_cell(0, 5, f"       {justificativa_curta}")
        
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
    # Procura pelo primeiro '{' e último '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx+1]
        try:
            # Verifica se é um JSON válido
            return json.loads(json_str)
        except:
            # Se não for, tenta encontrar o JSON de outras formas
            pass
    
    # Tenta usar expressão regular para encontrar um bloco JSON
    import re
    json_pattern = r'\{(?:[^{}]|(?R))*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
    
    # Se tudo falhar, lança um erro detalhado
    raise ValueError(f"Não foi possível extrair JSON válido da resposta: {text[:100]}...")

# Estilo visual - MANTIDO DO ORIGINAL
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
.script-usado {
    background-color: #e6ffe6;
    padding: 10px;
    border-left: 5px solid #00C100;
    border-radius: 6px;
    margin-bottom: 10px;
}
.script-nao-usado {
    background-color: #ffcccc;
    padding: 10px;
    border-left: 5px solid #FF0000;
    border-radius: 6px;
    margin-bottom: 10px;
}
.criterio-sim {
    background-color: #e6ffe6;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 5px;
    border-left: 5px solid #00C100;
}
.criterio-nao {
    background-color: #ffcccc;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 5px;
    border-left: 5px solid #FF0000;
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
.criterio-eliminatorio {
    background-color: #ffcccc;
    padding: 10px;
    border-radius: 6px;
    margin-top: 20px;
    border: 2px solid #FF0000;
    font-weight: bold;
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
</style>
""", unsafe_allow_html=True)

# Função para determinar classe de progresso - MANTIDA DO ORIGINAL
def get_progress_class(value):
    if value >= 70:
        return "progress-high"
    elif value >= 50:
        return "progress-medium"
    else:
        return "progress-low"

# Função para verificar status do script - MANTIDA DO ORIGINAL
def get_script_status_class(status):
    if status.lower() == "completo" or status.lower() == "sim":
        return "script-usado"
    else:
        return "script-nao-usado"

# Modelo fixo: GPT-4 Turbo - MANTIDO DO ORIGINAL
modelo_gpt = "gpt-4-turbo"

# Título - MANTIDO DO ORIGINAL
st.title("MonitorAI")
st.write("Análise inteligente de ligações: avaliação de atendimento ao cliente e conformidade com processos.")

# Upload de áudio - MANTIDO DO ORIGINAL
uploaded_file = st.file_uploader("Envie o áudio da ligação (.mp3)", type=["mp3"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.audio(uploaded_file, format='audio/mp3')

    if st.button("🔍 Analisar Atendimento"):
        # Transcrição via Whisper - MANTIDO DO ORIGINAL
        with st.spinner("Transcrevendo o áudio..."):
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            transcript_text = transcript.text

        with st.expander("Ver transcrição completa"):
            st.code(transcript_text, language="markdown")

        # Prompt - NOVO COM LÓGICA DE GRUPOS + TODAS AS INSTRUÇÕES ORIGINAIS
        prompt = f"""
Você é um especialista em atendimento ao cliente da Carglass. Avalie a transcrição a seguir usando a nova estrutura de GRUPOS.

TRANSCRIÇÃO:
\"\"\"{transcript_text}\"\"\"

ESTRUTURA DE AVALIAÇÃO POR GRUPOS:

A avaliação é dividida em 4 GRUPOS. REGRA CRÍTICA: Se qualquer item dentro de um grupo falhar (receber "não"), TODO O GRUPO recebe 0 pontos.

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

INSTRUÇÕES DETALHADAS DE AVALIAÇÃO (MANTIDAS DO SISTEMA ORIGINAL):

1. TÉCNICA DO ECO (Item 5) - AVALIAÇÃO RIGOROSA:

MARQUE COMO "SIM" SE QUALQUER UMA DAS CONDIÇÕES ABAIXO FOR ATENDIDA:

### CONDIÇÃO A - SOLETRAÇÃO FONÉTICA (APROVAÇÃO AUTOMÁTICA):
- O atendente fez soletração fonética de QUALQUER informação principal (placa, telefone ou CPF)
- Exemplos válidos: "R de rato, W de Washington, F de faca", "rato, sapo, xícara", "A de avião, B de bola"
- IMPORTANTE: Uma única soletração fonética é suficiente para marcar "SIM"

### CONDIÇÃO B - ECO MÚLTIPLO:
- O atendente repetiu (completa ou parcialmente) PELO MENOS 2 informações principais:
  * Placa do veículo
  * Telefone principal 
  * CPF
  * Telefone secundário (quando fornecido)

### CONDIÇÃO C - ECO PARCIAL (APROVAÇÃO FLEXÍVEL):
- O atendente repetiu parte significativa de uma informação principal
- Exemplos válidos: 
  * Cliente: "0800-703-0203" → Atendente: "0203" ✓ (últimos dígitos)
  * Cliente: "679-997-812" → Atendente: "812" ✓ (parte final)
  * Cliente: "54-3381-5775" → Atendente: "5775" ✓ (últimos dígitos)
- IMPORTANTE: Eco parcial de dígitos finais é válido mesmo sem confirmação explícita

### CONDIÇÃO D - ECO INTERROGATIVO CONFIRMADO:
- O atendente repetiu informação com tom interrogativo E o cliente confirmou
- Exemplos válidos:
  * "54-3381-5775?" → Cliente: "Isso"
  * "É 79150-005?" → Cliente: "Sim"

### NÃO É ECO VÁLIDO:
- Apenas "ok", "certo", "entendi", "perfeito" sem repetir informação
- Repetição sem confirmação do cliente quando necessária
- Eco de informações não principais (nome, endereço sem número)

2. SCRIPT LGPD (Item 4): O atendente deve mencionar explicitamente que o telefone será compartilhado com o prestador de serviço, com ênfase em privacidade ou consentimento. As seguintes variações são válidas:
   - Você permite que a nossa empresa compartilhe o seu telefone com o prestador que irá lhe atender?
   - Podemos compartilhar seu telefone com o prestador que irá realizar o serviço?
   - Seu telefone pode ser informado ao prestador que irá realizar o serviço?
   - O prestador pode ter acesso ao seu número para realizar o agendamento do serviço?
   - Você autoriza o compartilhamento do telefone informado com o prestador que irá te atender?
   - Você autoriza a enviar notificações no telefone WhatsApp (ou similar)

3. SOLICITAÇÃO DE DADOS DO CADASTRO (Item 3) - AVALIAÇÃO RIGOROSA:

MARQUE COMO "SIM" APENAS SE O ATENDENTE SOLICITOU EXPLICITAMENTE TODOS OS 6 DADOS OBRIGATÓRIOS:

### DADOS OBRIGATÓRIOS (6 elementos):
1. **NOME** do cliente
2. **CPF** do cliente
3. **PLACA** do veículo
4. **ENDEREÇO** do cliente
5. **TELEFONE PRINCIPAL** (1º telefone)
6. **TELEFONE SECUNDÁRIO** (2º telefone)

### CRITÉRIO DE "SOLICITAÇÃO" VÁLIDA:
- O atendente deve PERGUNTAR/PEDIR explicitamente cada dado
- Exemplos válidos:
  * "Qual é o seu nome completo?"
  * "Pode me informar o seu CPF?"
  * "Qual a placa do veículo?"
  * "Qual é o seu endereço?"
  * "Me passa um telefone para contato?"
  * "Tem um segundo telefone?"

### NÃO É SOLICITAÇÃO VÁLIDA:
- Cliente se identificar espontaneamente ("Meu nome é João")
- Atendente apenas confirmar dados já fornecidos
- Dados já visíveis no sistema sem confirmação
- Perguntar "mais algum número?" sem especificar que precisa de 2º telefone

### EXCEÇÃO PARA BRADESCO/SURA/ALD:
- **CPF e ENDEREÇO** podem ser dispensados APENAS se o atendente CONFIRMAR explicitamente que já estão no sistema
- Exemplos válidos de dispensa:
  * "Vejo aqui que já temos seu CPF no sistema"
  * "Seu endereço já consta aqui no cadastro"
  * "Localizei seus dados completos no sistema"
- IMPORTANTE: Simples omissão sem justificativa = FALSO

### TELEFONE SECUNDÁRIO - REGRA ESPECIAL:
- Deve ser solicitado OBRIGATORIAMENTE para todas as seguradoras
- "Cliente não tem" ou "só tenho esse" NÃO dispensa a solicitação
- O atendente deve perguntar explicitamente por um segundo número
- Exemplo correto: "Quer deixar uma segunda opção de telefone?"

4. CONFIRMAÇÃO DE DANOS NO VEÍCULO (Item 9): Deve confirmar data e motivo da quebra, registro do item, dano na pintura e demais informações necessárias (tamanho da trinca, LED, Xenon, etc).

5. CONFIRMAÇÃO DE CIDADE E LOJA (Item 10): ATENÇÃO - Ambos os critérios são obrigatórios: confirmar cidade E selecionar loja.

6. SCRIPT DE ENCERRAMENTO (Item 14): O script correto é:
"Obrigada por me aguardar! O seu atendimento foi gerado, e em breve receberá dois links no whatsapp informado, para acompanhar o pedido e realizar a vistoria. Lembrando que o seu atendimento tem uma franquia de XXX que deverá ser paga no ato do atendimento. Te ajudo com algo mais? Ao final do atendimento terá uma pesquisa de Satisfação, a nota 5 é a máxima, tudo bem? Agradeço o seu contato, tenha um excelente dia!"

Deve incluir: prazo de validade, franquia, link de acompanhamento e vistoria, orientação para aguardar contato.

7. CRITÉRIOS ELIMINATÓRIOS (cada um resulta em penalização se ocorrer):
- Ofereceu/garantiu algum serviço que o cliente não tinha direito
- Preencheu ou selecionou o Veículo/peça incorretos
- Agiu de forma rude, grosseira, não deixando o cliente falar
- Encerrou a chamada ou transferiu sem conhecimento do cliente
- Falou negativamente sobre a Carglass, afiliados, seguradoras ou colegas
- Forneceu informações incorretas ou fez suposições infundadas
- Comentou sobre serviços de terceiros sem autorização

REGRAS DE PONTUAÇÃO:
1. Avalie cada item individualmente (true/false)
2. Se TODOS os itens de um grupo forem true, o grupo recebe a pontuação total
3. Se QUALQUER item de um grupo for false, o grupo inteiro recebe 0 pontos
4. A pontuação final é a soma dos pontos de todos os grupos aprovados

Retorne APENAS um JSON válido com esta estrutura:

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
          "justificativa": "Explicação detalhada com evidências da transcrição"
        }}
      ]
    }}
  ],
  "pontuacao_total": {{
    "obtida": 0-86,
    "maxima": 86,
    "percentual": 0-100
  }},
  "resumo_geral": "Análise geral do atendimento com foco nos grupos aprovados/reprovados",
  "pontos_positivos": ["lista de pontos fortes identificados"],
  "pontos_melhoria": ["lista de melhorias necessárias"]
}}

IMPORTANTE: 
- Seja rigoroso na avaliação. Um único item não atendido reprova todo o grupo!
- Todas as justificativas devem ser específicas e baseadas em evidências da transcrição
- Retorne APENAS o JSON, sem texto adicional
"""

        with st.spinner("Analisando a conversa..."):
            try:
                response = client.chat.completions.create(
                    model=modelo_gpt,
                    messages=[
                        {"role": "system", "content": "Você é um analista especializado em atendimento. Responda APENAS com o JSON solicitado, sem texto adicional, sem marcadores de código como ```json, e sem explicações."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                result = response.choices[0].message.content.strip()

                # Mostrar resultado bruto para depuração
                with st.expander("Debug - Resposta bruta"):
                    st.code(result, language="json")
                
                # Tentar extrair e validar o JSON
                try:
                    if not result.startswith("{"):
                        analysis = extract_json(result)
                    else:
                        analysis = json.loads(result)
                except Exception as json_error:
                    st.error(f"Erro ao processar JSON: {str(json_error)}")
                    st.text_area("Resposta da IA:", value=result, height=300)
                    st.stop()

                # EXIBIÇÃO DOS RESULTADOS - NOVA ESTRUTURA DE GRUPOS

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
