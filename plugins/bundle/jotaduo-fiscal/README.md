# Jotaduo Fiscal — NFe/NFSe/NFCe BR

> **ID:** `jotaduo-fiscal` · **Versão:** 1.0.0 · **Idioma:** pt-BR

Plugin fiscal brasileiro para o Jotaduo AI Platform (fork JotaDuo). Ele registra
um agente especialista fiscal, ferramentas LLM-callable e uma API HTTP para
emitir e acompanhar NF-e, NFS-e e NFC-e via provedores fiscais.

## O que ele instala

| Componente | Descrição |
|---|---|
| Agente | `jotaduo-fiscal`, papel `fiscal`, persona pt-BR |
| Tools | `emitir_nfe`, `emitir_nfse`, `emitir_nfce`, `consultar_nota`, `cancelar_nota`, `carta_correcao`, `inutilizar_numeracao`, `baixar_xml_danfe` |
| HTTP API | `/api/fiscal/health`, `/api/fiscal/notas/{chave}`, `/api/fiscal/webhook/{provider}` |
| Provider padrão | Focus NFe (`FISCAL_PROVIDER=focus_nfe`) |
| Ambiente padrão | Homologação (`FISCAL_AMBIENTE=homologacao`) |

## Instalação

1. Mantenha a pasta em `plugins/bundle/jotaduo-fiscal/`.
2. Instale dependências do plugin no ambiente do backend, se necessário:

```powershell
pip install -r plugins\bundle\jotaduo-fiscal\requirements.txt
```

3. Reinicie o backend do Jotaduo/JotaDuo.
4. Confira o agente `jotaduo-fiscal` na área de agentes.
5. Configure as variáveis de ambiente no Console.

## Configuração

Variáveis principais:

```env
FISCAL_PROVIDER=focus_nfe
FISCAL_API_KEY=sandbox
FISCAL_AMBIENTE=homologacao
EMPRESA_CNPJ=12345678000199
EMPRESA_IE=123456789
EMPRESA_REGIME_TRIBUTARIO=simples_nacional
```

Use `FISCAL_API_KEY=sandbox` para testar o scaffold sem enviar chamadas reais.
Sem `FISCAL_API_KEY` e `EMPRESA_CNPJ`, as ferramentas retornam erro seguro.

Variável opcional para webhooks:

```env
FISCAL_WEBHOOK_SECRET=um-segredo-compartilhado
```

Quando definida, o webhook valida `x-focusnfe-signature` ou
`x-webhook-signature` como segredo simples ou HMAC SHA-256.

## Exemplos via chat

- "Consulte a nota com chave 3524..."
- "Prepare uma NF-e para o CNPJ 12.345.678/0001-99 com estes itens..."
- "Baixe o DANFE em PDF da nota 3524..."
- "Cancele a nota 3524... com justificativa: erro operacional na emissão"

Para cancelamento e inutilização, o agente é instruído a pedir confirmação
humana explícita antes de executar.

## Exemplos HTTP

Health sem vazamento de segredo:

```powershell
curl http://localhost:8000/api/fiscal/health
```

Consultar nota:

```powershell
curl http://localhost:8000/api/fiscal/notas/REF-OU-CHAVE
```

Webhook de provedor:

```powershell
curl -X POST http://localhost:8000/api/fiscal/webhook/focus_nfe `
  -H "Content-Type: application/json" `
  -d '{"ref":"jotaduo-nfe-1","status":"autorizado"}'
```

## Provedores suportados

| Provider | Status |
|---|---|
| `focus_nfe` | Adapter padrão com assinatura HTTP real e stub seguro para `sandbox` |
| `webmania` | Stub estrutural pronto para implementação |
| `nfe_io` / `nfe.io` | Stub estrutural pronto para implementação |

A abstração fica em `providers/base.py`; novas integrações devem implementar
`AbstractFiscalProvider` e retornar sempre `{"ok": bool, "data": ..., "error": ...}`.

## Compliance e segurança

- Homologação é o padrão para evitar emissão real acidental.
- O agente alerta quando o ambiente estiver em produção.
- CNPJ/CPF são tratados como dados sensíveis; não exponha XML fiscal sem base
  legal ou autorização.
- A emissão fiscal depende de contador, parametrização tributária e dados
  corretos do ERP/empresa.
- Nunca coloque tokens, certificados ou senhas no código-fonte.

## Troubleshooting

| Sintoma | Possível causa | Ação |
|---|---|---|
| `Configuração fiscal incompleta` | Falta `FISCAL_API_KEY` ou `EMPRESA_CNPJ` | Preencha as env vars no Console |
| `EMPRESA_CNPJ deve conter 14 dígitos` | CNPJ inválido | Informe apenas CNPJ real do emitente |
| Provider retorna stub | `FISCAL_API_KEY=sandbox` ou provider não implementado | Configure token real ou implemente adapter |
| Webhook 401 | Assinatura ausente/inválida | Confira `FISCAL_WEBHOOK_SECRET` e header |
| Rejeição SEFAZ | Dados fiscais incompletos/incorretos | Consulte contador e revise payload |

## Arquitetura

```text
plugins/bundle/jotaduo-fiscal/
├── plugin.py              # lifecycle, router/tools/agent registration
├── agents_setup.py        # registra o agente jotaduo-fiscal
├── tools/fiscal_tools.py  # funções LLM-callable validadas com Pydantic
├── providers/             # abstração multi-provider
├── routers/fiscal_router.py
└── agents/fiscal_prompt.py
```
