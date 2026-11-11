# Regras de desempate v1 (gabarito do triador de marketplace)

Decididas em 09/11/2026, antes de qualquer rodada do ajuste. Valem para o gabarito dos dois lotes (`ajuste-40-v2.csv` e `prova-40-v2.csv`) e devem entrar no prompt do n8n no passo de ajuste. Elas detalham as regras do escopo, não mudam nenhuma.

## Bloco para colar no prompt (logo depois de PRIORIDADE)

```
REGRAS DE DESEMPATE:
1. A nota não decide a categoria. Se a ressalva for um problema da lista (item errado, faltando ou danificado; atraso; cobrança), classifique pelo problema. Use "outros" (elogio com ressalva) só quando a ressalva não for um desses problemas: embalagem amassada sem dano ao conteúdo, app confuso, sugestão.
2. Embalagem ou sacola danificada sem dano ao conteúdo: "outros", Baixa, Atendimento. Se o conteúdo foi afetado: "qualidade do pedido".
3. Item errado, faltando ou danificado que não inviabiliza o pedido: Média. Item impróprio para consumo, com risco à saúde, ou pedido inutilizável: Alta.
4. Atraso: chegou até cerca de 1 hora depois do combinado = Média. Passou de 1 hora, não chegou, ou consta como entregue sem ter chegado = Alta.
5. Dinheiro: use "preço" e Pagamentos quando houver valor a corrigir. Cobrança duplicada ou cobrança do valor inteiro sem o pedido (cancelado, recusado ou não entregue) = Alta. Diferença pequena (taxa, cupom, cashback, poucos reais) = Média.
6. Dúvida sem valor a corrigir (regra de cupom ou cashback, forma de pagamento, conta, cadastro, uso do app): "outros", Baixa, Atendimento.
7. Reclamação que o próprio texto diz que já foi resolvida: categoria = o problema original; prioridade Baixa; time Atendimento (não há ação pendente, só registro).
8. Detalhes que não descrevem o problema (horário da refeição, forma de pagamento usada, onde a pessoa mora, quantos pedidos fez na semana) não mudam a classificação.
```

## Por que a regra de cupom/cashback ficou assim (regras 5 e 6)

O escopo deixava uma ambiguidade: "Pagamentos: cobrança, cupom, valor" e "Atendimento: dúvida". O critério escolhido é operacional: **Pagamentos recebe quando existe dinheiro a corrigir** (cobrança errada, estorno, desconto que deveria ter sido aplicado, cashback que sumiu). Pergunta sobre regra de cupom ou cashback não tem valor a corrigir e se responde com informação, então fica com Atendimento. Mandar dúvidas para Pagamentos encheria o time especializado de perguntas de FAQ. A prioridade Baixa para "dúvida de cupom" já estava no escopo.

Pares no gabarito que exercitam a fronteira:

| Situação | Classificação |
|---|---|
| "O cupom PRIMEIRA10 vale pra mercado?" (ajuste 37) | outros, Baixa, Atendimento |
| "Cupom de R$ 5 não aplicou" (ajuste 14) | preço, Média, Pagamentos |
| "Vocês aceitam vale-refeição?" (ajuste 36) | outros, Baixa, Atendimento |
| "O cashback de R$ 10 sumiu" (ajuste 17) | preço, Média, Pagamentos |

## Mudanças no ajuste-40 (v2)

- 16 linhas duplicadas trocadas por casos novos (ids 8, 11, 17, 19, 20, 22, 25, 26, 28, 31, 32, 34, 35, 36, 38, 40). O lote agora tem 40 situações distintas, de 9 a 11 por categoria, 20 avaliações e 20 tickets.
- Id 12: removido "Detalhe: foi no jantar.", que contradizia "só atrasou o almoço".
- As 23 linhas não mexidas mantêm a assinatura. As 17 alteradas estão com `assinado_por` vazio para nova assinatura.
- Nenhum texto do ajuste aparece na prova: a maior semelhança entre os dois lotes é 0,61, e vem de casos que aplicam a mesma regra com palavras diferentes.
