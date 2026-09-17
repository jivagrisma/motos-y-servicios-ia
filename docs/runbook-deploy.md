# Runbook — Despliegue CI/CD

## Qué automatiza `deploy.yml`
1. **Build** de las 2 imágenes (api, web) → Artifact Registry, tag = SHA del commit.
2. **Deploy** a Cloud Run (`motos-api`, `motos-web`), proyecto `motos-servicios-assessment-ia`.
3. **Smoke test** post-deploy (health del API + HTTP 200 de la web). Falla el workflow si la URL no responde.

Disparadores: `workflow_dispatch` (manual) y `push` a `main` (excluye cambios solo de docs).

## Disparar manualmente
```bash
gh workflow run deploy.yml --repo jivagrisma/motos-y-servicios-ia
```

## Monitorear
```bash
gh run list --repo jivagrisma/motos-y-servicios-ia --limit 3   # ver estado
gh run watch                     # seguir la ejecución en vivo (desde el directorio del repo)
gh run view <run-id> --log-failed   # logs si falló
```

## Verificación post-deploy
```bash
curl -s https://motos-api-53117453818.us-central1.run.app/api/health          # {"ok":true,...}
curl -s -o /dev/null -w "%{http_code}\n" https://motos-web-53117453818.us-central1.run.app/   # 200
curl -s -o /dev/null -w "%{http_code}\n" "https://motos-api-53117453818.us-central1.run.app/api/leads-del-dia"  # 400 = aislamiento activo
```

## Reglas de revisión (evaluación)
- El repo trabaja con **push directo a main** — decisión deliberada para un assessment de un solo desarrollador: exigir PR review bloquearía el despliegue sin aportar calidad (no hay segundo revisor).
- Para uso en equipo (como en Viajemos): activar en Settings → Rulesets → "Require a pull request before merging" + "Require status checks" (el job `deploy` sirve de check). Con eso, `workflow_dispatch` queda como vía de emergencia y el flujo normal es PR → review → merge → deploy automático.
- El secret `GCP_SA_KEY` pertenece a la service account `gh-deployer` con permisos mínimos (`run.admin`, `artifactregistry.writer`, `iam.serviceAccountUser`) solo en el proyecto dedicado. Rotar: crear key nueva → `gh secret set GCP_SA_KEY` → borrar key vieja.

## Rollback
```bash
gcloud run services replay-revision motos-api --region us-central1   # vuelve a la revisión anterior
gcloud run services replay-revision motos-web --region us-central1
```
O fijar tráfico a un tag: `gcloud run services update-traffic motos-api --to-revisions motos-api-00002-pd5=100 --region us-central1`
