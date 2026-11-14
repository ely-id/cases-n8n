# Congelamento do prompt v2

- **Data e hora:** 2026-11-10 13:22:53 -0300
- **Fluxo:** Triador de review e atendimento (`BQjYcn6JmGWBLzee`)
- **Versão publicada:** `0d251e0c-7952-4071-824a-bd3fdf056571`
- **versao_prompt:** `v2`
- **SHA-256 de `fluxo-n8n/prompt-v2-congelado.txt`:** `53bea33a2d85539a41a34072edcbb1bbe06a21d9a9a1b91acf5099dcad36662e`

## Comando exato usado para extrair o prompt

Os comandos rodam a partir de `marketplace/` (na raiz do repositório), com o container `n8n` no ar. Abre o banco só para leitura e pega o system prompt da versão publicada.

```sh
docker exec -i n8n node -e '
const sqlite3=require("/usr/local/lib/node_modules/n8n/node_modules/.pnpm/sqlite3@5.1.7_bluebird@3.7.2_supports-color@8.1.1/node_modules/sqlite3");
const db=new sqlite3.Database("/home/node/.n8n/database.sqlite",sqlite3.OPEN_READONLY);
db.get("SELECT h.nodes FROM workflow_entity w JOIN workflow_history h ON h.workflowId=w.id AND h.versionId=w.activeVersionId WHERE w.id=?",["BQjYcn6JmGWBLzee"],(e,r)=>{
  if(e||!r){console.error(e?e.message:"versao publicada nao encontrada");process.exit(1)}
  const nodes=typeof r.nodes==="string"?JSON.parse(r.nodes):r.nodes;
  process.stdout.write(nodes.find(n=>n.name==="IA classifica o relato").parameters.messages.messageValues[0].message);
  db.close();
});' > fluxo-n8n/prompt-v2-congelado.txt
```

## Para repetir antes da prova

Não use o `>` acima, porque ele sobrescreve o arquivo congelado. Troque o final `> fluxo-n8n/prompt-v2-congelado.txt` por `| sha256sum` e compare com o SHA-256 registrado aqui.
