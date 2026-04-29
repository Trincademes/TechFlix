# 🤖 TechFix AI Assistant

Sistema web de atendimento inteligente desenvolvido com **Python Flask**, **SQLite** e integração com a **API da Groq**, simulando um agente de IA para pré-atendimento, captação de leads e suporte inicial para empresas.

O projeto foi criado com foco em portfólio, demonstrando a aplicação prática de inteligência artificial em um cenário real de negócio.

---

## 📌 Visão Geral

O **TechFix AI Assistant** é um agente virtual de atendimento para a empresa fictícia **TechFix Soluções Digitais**, uma empresa de tecnologia voltada para pequenas empresas.

A aplicação permite que um cliente converse com um assistente inteligente, tire dúvidas sobre serviços, informe suas necessidades e tenha seus dados registrados automaticamente em um painel administrativo.

O sistema atua como um pré-atendente comercial, coletando informações importantes para transformar conversas em possíveis leads.

---

## 🎯 Objetivo do Projeto

O objetivo principal do projeto é simular um sistema real de atendimento automatizado com IA, capaz de:

- Atender clientes de forma natural
- Responder dúvidas sobre serviços
- Coletar nome e telefone
- Identificar a necessidade do cliente
- Classificar intenção e prioridade
- Registrar conversas no banco de dados
- Exibir os leads em um painel administrativo
- Apoiar uma equipe comercial ou técnica no atendimento inicial

---

## 🏢 Empresa Fictícia

### TechFix Soluções Digitais

A TechFix é uma empresa fictícia criada para contextualizar o projeto.

Ela oferece serviços como:

- Criação de sites profissionais
- Landing pages
- Lojas virtuais
- Sistemas web
- Dashboards
- Automação de processos
- Suporte técnico

Esse contexto permite que o agente de IA tenha uma função clara dentro do sistema: realizar o primeiro atendimento e organizar informações para uma equipe humana.

---

## 🧠 Como o Agente de IA Funciona

O agente foi desenvolvido para seguir um fluxo de atendimento mais natural e menos cansativo para o usuário.

Ele não apenas responde mensagens, mas também conduz a conversa de forma estratégica.

### Fluxo principal:

1. Cumprimenta o cliente
2. Solicita o nome
3. Solicita telefone para contato
4. Entende o problema ou necessidade
5. Responde dúvidas específicas
6. Aprofunda o contexto do cliente
7. Classifica a conversa
8. Registra o atendimento no banco
9. Informa que a equipe entrará em contato
10. Sugere continuidade para alinhamento ou reunião

---

## 💬 Exemplo de Conversa

```text
Cliente: Olá, vocês fazem loja virtual?

Agente: Sim, fazemos loja virtual para empresas que querem vender online, com estrutura para produtos, pedidos e gestão básica. Para eu registrar seu atendimento, qual é o seu nome?

Cliente: Pedro

Agente: Perfeito, Pedro. Para nossa equipe conseguir retornar depois, qual telefone podemos usar?

Cliente: 15999999999

Agente: Obrigado, Pedro. Me conta um pouco melhor: o que você quer desenvolver ou resolver?

Cliente: Quero uma loja virtual para vender roupas

Agente: Entendi, Pedro. Então você está buscando uma loja virtual para vender roupas online. Você pretende vender poucos produtos inicialmente ou já terá um catálogo maior?

Cliente: Vou começar com poucos produtos

Agente: Perfeito, Pedro. Registrei as informações do seu atendimento:
- Nome: Pedro
- Telefone: 15999999999
- Necessidade: Loja virtual / E-commerce
- Objetivo: começar com poucos produtos

Vou encaminhar essas informações para a equipe da TechFix. Eles poderão entrar em contato pelo telefone informado para alinhar os detalhes e, se fizer sentido, marcar uma reunião.
