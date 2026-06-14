# Nexora Pix — Cobranças e Conciliação BR

Plugin bundle para a Nexora AI Platform com cobrança Pix imediata, cobrança com vencimento, recorrência, conciliação, webhooks, devolução e suporte multi-PSP.

## Instalação

1. Copie este diretório para `plugins/bundle/nexora-pix/`.
2. Instale/ative o plugin pela Console da plataforma.
3. Configure as variáveis de ambiente abaixo.
4. Reinicie a plataforma para registrar o agente `nexora-cobranca`, rotas e ferramentas.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `PIX_PROVIDER` | `asaas` | Provedor Pix (`asaas`, `mercado_pago`, `pagbank`, `bcb_direct`). |
| `PIX_API_KEY` | vazio | Token do PSP. Use `sandbox` para respostas mockadas. |
| `PIX_AMBIENTE` | `sandbox` | Ambiente (`sandbox` ou `production`). |
| `PIX_CHAVE` | vazio | Chave Pix oficial do recebedor para QR estático. |
| `PIX_WEBHOOK_SECRET` | vazio | Segredo HMAC opcional para validar callbacks. |

Não versionar segredos. Configure-os pela Console ou pelo ambiente do processo.

## Exemplos no chat

- “Crie uma cobrança Pix de R$ 149,90 para Maria Silva, CPF 123.456.789-09, referente à consulta.”
- “Gere Pix com vencimento em 2025-02-10 para CNPJ 12.345.678/0001-90, R$ 980, multa 2% e juros 1%.”
- “Crie recorrência mensal de R$ 79,90 por 12 cobranças, início em 2025-01-05.”
- “Consulte a cobrança pelo txid abc123...”
- “Concilie o txid X com valor recebido R$ 149,90 e E2EID E123...”
- “Faça devolução Pix de R$ 50,00 pelo E2EID E123... motivo duplicidade.”

## Webhook do PSP

Configure no PSP a URL pública:

```text
POST https://SEU-DOMINIO/api/pix/webhook/asaas
```

Se `PIX_WEBHOOK_SECRET` estiver definido, envie a assinatura HMAC SHA-256 do corpo bruto em um destes headers:

- `X-Pix-Signature: sha256=<hex>`
- `X-Hub-Signature-256: sha256=<hex>`

O webhook normaliza o payload, atualiza a cobrança local por `txid` e retorna HTTP 200.

## Provedores

- **Asaas**: implementação padrão. Usa endpoints v3 e header `access_token`. Com `PIX_API_KEY=sandbox`, retorna respostas realistas sem chamar API externa.
- **Mercado Pago**: stub pronto para expansão.
- **PagBank**: stub pronto para expansão.
- **BCB Direct**: stub para integração direta futura com mTLS e credenciais SPI/DICT.

## Idempotência e conciliação

As cobranças são salvas em SQLite no arquivo:

```text
plugins/bundle/nexora-pix/store/pix.db
```

O plugin consulta `(provider, txid)` antes de criar cobranças e usa `INSERT OR IGNORE` para evitar duplicidade. O `txid` segue a especificação Pix: alfanumérico com 26 a 35 caracteres.

Adicione `plugins/bundle/nexora-pix/store/pix.db` ao `.gitignore` do repositório/implantação. Este arquivo é estado local operacional e não deve ser commitado.

## Troubleshooting

- **Cobrança não aparece**: verifique `PIX_PROVIDER`, `PIX_API_KEY` e logs `qwenpaw.plugin.nexora-pix`.
- **Webhook retorna 401**: confirme o HMAC e o valor de `PIX_WEBHOOK_SECRET`.
- **CPF/CNPJ inválido**: envie apenas CPF com 11 dígitos ou CNPJ com 14 dígitos, com ou sem pontuação.
- **QR estático sem chave**: configure `PIX_CHAVE` ou passe `chave_pix` explicitamente.
- **Produção Asaas**: defina `PIX_AMBIENTE=production` e um token real em `PIX_API_KEY`.
