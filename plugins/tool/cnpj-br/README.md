# CNPJ Brasil — Consultas Cadastrais

Plugin tool-type leve para consultas cadastrais brasileiras na Nexora AI Platform.

## O que faz

- Consulta CNPJ com dados normalizados de razão social, situação, endereço, CNAE, sócios, Simples Nacional e MEI.
- Consulta CEP e retorna endereço.
- Valida CPF offline pelo dígito verificador.
- Valida inscrição estadual offline para SP, RJ, MG, RS, PR, BA, PE, GO, DF, SC, ES e CE.
- Extrai dados do Simples Nacional/MEI a partir do CNPJ.
- Enriquece leads com score comercial simples de 0 a 100.

## Fontes públicas

A fonte principal é a BrasilAPI, gratuita e sem chave de API. Para CNPJ, o plugin pode usar ReceitaWS como fallback público quando a BrasilAPI falhar.

## Exemplos no chat

- `consulte o CNPJ 00.000.000/0001-91`
- `valide o CPF 529.982.247-25`
- `busque o CEP 01001-000`
- `valide a inscrição estadual 110042490114 para SP`
- `esse CNPJ é optante pelo Simples Nacional? 00.000.000/0001-91`
- `enriqueça o lead 00.000.000/0001-91 com email contato@empresa.com.br`

## Limitações

- CPF é somente validação offline por dígitos verificadores. Não consulta dados pessoais na Receita Federal.
- ReceitaWS possui rate limit e pode retornar erro 429 em uso intenso.
- Dados públicos podem estar desatualizados ou incompletos conforme a fonte.
- A validação de inscrição estadual cobre os estados listados acima; outras UFs retornam erro de UF não suportada.

## Configuração opcional

Nenhuma chave é obrigatória. Os campos abaixo podem ser ajustados por ferramenta:

| Campo | Padrão | Descrição |
|---|---:|---|
| `provider_fallback` | `auto` | `auto` usa BrasilAPI primeiro e ReceitaWS como fallback; também aceita `brasilapi` ou `receitaws`. |
| `timeout` | `15` | Timeout HTTP em segundos, mínimo 5 e máximo 60. |
| `cache_ttl_seconds` | `3600` | TTL do cache em memória; use `0` para desativar. |

## Ferramentas

- `consultar_cnpj`
- `consultar_cep`
- `consultar_cpf`
- `validar_inscricao_estadual`
- `consultar_simples_nacional`
- `enriquecer_lead`
