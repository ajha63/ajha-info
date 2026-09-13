# Playbook de despliegue de ajha.me

Este flujo publica el contenido estatico aprobado en `arn:aws:s3:::ajha.me` y crea invalidaciones en `arn:aws:cloudfront::554982632606:distribution/E2EWY8K28XHSNA`.

## Estado verificado antes del primer despliegue

- Repositorio y rama predeterminada: `ajha63/ajha-info`, `main`.
- Cuenta AWS: `554982632606`.
- Bucket: `ajha.me`, region `us-east-1`, cifrado SSE-S3 AES256.
- CloudFront: distribucion activa `E2EWY8K28XHSNA`, HTTPS forzado, origen S3 mediante OAI `EQVRY0Z9VPLGF`.
- La politica y ACL observadas no exponen publicamente el bucket. No hay hosting web S3 directo.
- El bucket no tiene versionado, Public Access Block ni Ownership Controls configurados. Resolver estos controles de infraestructura mediante un cambio separado y aprobado; el pipeline no modifica politicas, ACL, versionado ni CloudFront.
- El perfil local `alhernan` resolvio a un usuario IAM directo. Se uso solo para inventario de lectura; no debe usarse para publicar. El pipeline requiere roles temporales OIDC.
- La autenticacion local de GitHub debe renovarse antes de crear el PR porque el token de `gh` esta vencido.

## Configuracion unica requerida

1. Revisar y desplegar `infra/github-actions-oidc.yml` con una sesion administrativa temporal. La plantilla crea el proveedor OIDC y dos roles:
   - Rol de plan: `s3:ListBucket`, `s3:GetBucketLocation` sobre el bucket y `s3:GetObject` sobre sus objetos.
   - Rol de despliegue: los permisos anteriores, `s3:PutObject`, `cloudfront:CreateInvalidation` y `cloudfront:GetInvalidation`. Agregar `s3:DeleteObject` solo cuando se aprueben bajas administradas por el pipeline.
2. Las politicas de confianza usan audience `sts.amazonaws.com` y los subjects inmutables confirmados por GitHub:
   - Plan: `repo:ajha63@560156/ajha-info@1367452827:ref:refs/heads/main`.
   - Despliegue: `repo:ajha63@560156/ajha-info@1367452827:environment:production`.
   Volver a consultar la configuracion OIDC del repositorio si cambia su owner, nombre o identidad inmutable. No usar comodines que permitan otros repositorios.
3. Crear las variables de Actions `AWS_READ_ROLE_ARN` y `AWS_DEPLOY_ROLE_ARN` con los ARN de esos roles. No guardar access keys en GitHub Secrets.
4. Configurar el environment `production` exclusivamente con `ajha63` como required reviewer y limitar despliegues a `main`. Activar `prevent self-review` cuando otra persona o una identidad de automatizacion inicie el workflow; si `ajha63` es tambien quien lo inicia, esa opcion impediria que el owner apruebe. El workflow comprueba el reviewer esperado antes de solicitar la sesion AWS de escritura.
5. Renovar GitHub CLI localmente con `gh auth login -h github.com` sin compartir el token.

La politica inicial no incluye `s3:DeleteObject`; el primer despliegue no contiene bajas. Agregar ese permiso mediante revision de infraestructura solo cuando exista una baja explicita de un objeto marcado como administrado por el pipeline.

## Preparacion y pull request

1. Trabajar en `codex/ajha-me-deployment-pipeline` y revisar que solo contenga el pipeline, scripts, pruebas y este playbook.
2. Ejecutar `npm ci --ignore-scripts`, `python3 -m unittest discover -s tests`, `npm run validate:html` y construir un artefacto en un directorio temporal con `scripts/build_site.py`.
3. Crear el PR hacia `main`. Revisar los checks y fusionarlo con aprobacion del owner.

## Ejecucion del primer despliegue

1. Abrir Actions, elegir `Deploy ajha.me` y ejecutar desde `main`.
2. Introducir el SHA completo del commit de `main` que se desea publicar. Usar `[]` para `delete_paths_json` en el primer despliegue: los objetos heredados no tienen la marca de gestion del pipeline y no se eliminaran automaticamente.
3. Revisar en el resumen del job `plan` el SHA, digest del artefacto, digest del plan, altas/cambios, bajas e invalidaciones.
4. El owner aprueba el environment `production` solo si esos datos coinciden con el alcance esperado. Un cambio concurrente en S3 modifica el plan y bloquea la ejecucion.
5. El job carga archivos nuevos o modificados, mantiene headers de cache existentes, publica HTML al final, espera la invalidacion y compara por SHA-256 los objetos servidos por `https://ajha.me`.

## Rollback

El bucket no tiene versionado. Antes del primer despliegue, conservar una copia privada de los objetos que el plan reemplazara. Si falla la verificacion, restaurar esa copia con una sesion temporal aprobada, invalidar las mismas rutas y documentar el incidente. Activar versionado mediante un cambio de infraestructura aprobado mejora este proceso.

## Manejo de credenciales

Usar OIDC en Actions o SSO/assume-role local. No pegar access keys, secret keys, session tokens, MFA ni respuestas STS en chats, comandos, PR, logs o archivos. Verificar siempre la cuenta `554982632606` y el rol esperado antes de escribir.
