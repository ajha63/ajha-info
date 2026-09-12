# Playbook de despliegue de ajha.info

Este flujo publica el contenido estatico aprobado en `arn:aws:s3:::ajha.info` y crea invalidaciones en `arn:aws:cloudfront::554982632606:distribution/E2EWY8K28XHSNA`.

## Estado verificado antes del primer despliegue

- Repositorio y rama predeterminada: `ajha63/ajha-info`, `main`.
- Cuenta AWS: `554982632606`.
- Bucket: `ajha.info`, region `us-east-1`, cifrado SSE-S3 AES256.
- CloudFront: distribucion activa `E2EWY8K28XHSNA`, HTTPS forzado, origen S3 mediante OAI `EQVRY0Z9VPLGF`.
- La politica y ACL observadas no exponen publicamente el bucket. No hay hosting web S3 directo.
- El bucket no tiene versionado, Public Access Block ni Ownership Controls configurados. Resolver estos controles de infraestructura mediante un cambio separado y aprobado; el pipeline no modifica politicas, ACL, versionado ni CloudFront.
- El perfil local `alhernan` resolvio a un usuario IAM directo. Se uso solo para inventario de lectura; no debe usarse para publicar. El pipeline requiere roles temporales OIDC.
- La autenticacion local de GitHub debe renovarse antes de crear el PR porque el token de `gh` esta vencido.

## Configuracion unica requerida

1. Crear o identificar dos roles IAM temporales para GitHub OIDC:
   - Rol de plan: `s3:ListBucket`, `s3:GetBucketLocation` sobre el bucket y `s3:GetObject` sobre sus objetos.
   - Rol de despliegue: los permisos anteriores, `s3:PutObject`, `cloudfront:CreateInvalidation` y `cloudfront:GetInvalidation`. Agregar `s3:DeleteObject` solo cuando se aprueben bajas administradas por el pipeline.
2. Restringir las politicas de confianza al proveedor `token.actions.githubusercontent.com`, audience `sts.amazonaws.com` y subjects exactos de este repositorio:
   - Plan: ejecución desde `refs/heads/main`.
   - Despliegue: environment `production`.
   Verificar el formato actual del claim `sub`, incluidos claims inmutables si la organizacion los habilito. No usar comodines que permitan otros repositorios.
3. Crear las variables de Actions `AWS_READ_ROLE_ARN` y `AWS_DEPLOY_ROLE_ARN` con los ARN de esos roles. No guardar access keys en GitHub Secrets.
4. Configurar el environment `production` exclusivamente con `ajha63` como required reviewer y limitar despliegues a `main`. Activar `prevent self-review` cuando otra persona o una identidad de automatizacion inicie el workflow; si `ajha63` es tambien quien lo inicia, esa opcion impediria que el owner apruebe. El workflow comprueba el reviewer esperado antes de solicitar la sesion AWS de escritura.
5. Renovar GitHub CLI localmente con `gh auth login -h github.com` sin compartir el token.

## Preparacion y pull request

1. Trabajar en `codex/ajha-info-deployment-pipeline` y revisar que solo contenga el pipeline, scripts, pruebas y este playbook.
2. Ejecutar `npm ci --ignore-scripts`, `python3 -m unittest discover -s tests`, `npm run validate:html` y construir un artefacto en un directorio temporal con `scripts/build_site.py`.
3. Crear el PR hacia `main`. Revisar los checks y fusionarlo con aprobacion del owner.

## Ejecucion del primer despliegue

1. Abrir Actions, elegir `Deploy ajha.info` y ejecutar desde `main`.
2. Introducir el SHA completo del commit de `main` que se desea publicar. Usar `[]` para `delete_paths_json` en el primer despliegue: los objetos heredados no tienen la marca de gestion del pipeline y no se eliminaran automaticamente.
3. Revisar en el resumen del job `plan` el SHA, digest del artefacto, digest del plan, altas/cambios, bajas e invalidaciones.
4. El owner aprueba el environment `production` solo si esos datos coinciden con el alcance esperado. Un cambio concurrente en S3 modifica el plan y bloquea la ejecucion.
5. El job carga archivos nuevos o modificados, mantiene headers de cache existentes, publica HTML al final, espera la invalidacion y compara por SHA-256 los objetos servidos por `https://ajha.info`.

## Rollback

El bucket no tiene versionado. Antes del primer despliegue, conservar una copia privada de los objetos que el plan reemplazara. Si falla la verificacion, restaurar esa copia con una sesion temporal aprobada, invalidar las mismas rutas y documentar el incidente. Activar versionado mediante un cambio de infraestructura aprobado mejora este proceso.

## Manejo de credenciales

Usar OIDC en Actions o SSO/assume-role local. No pegar access keys, secret keys, session tokens, MFA ni respuestas STS en chats, comandos, PR, logs o archivos. Verificar siempre la cuenta `554982632606` y el rol esperado antes de escribir.
