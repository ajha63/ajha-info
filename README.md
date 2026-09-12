# ajha.info

Repositorio de mi página personal **[ajha.info](https://ajha.info/)**.

Este sitio funciona como mi espacio personal en Internet para presentar mi perfil profesional, compartir proyectos y publicar contenido sobre tecnología, operaciones en la nube, soporte TI, automatización e inteligencia artificial aplicada.

## Sobre el sitio

**ajha.info** está basado en la plantilla **Miniport** de [HTML5 UP](https://html5up.net/) y fue adaptado como una página personal de una sola vista con navegación por secciones.

El enfoque actual del sitio es **ejecutivo-práctico con base técnica**: explicar temas de TI de forma clara, conectar tecnología con operación real y convertir aprendizajes en contenido útil para líderes, equipos técnicos y profesionales de soporte.

## Secciones principales

- **Top:** presentación personal.
- **Resumen:** comunicación clara, operación con método y aprendizaje aplicado.
- **Work:** Cloud Operations, automatización de procesos y AI aplicada a TI.
- **Portfolio:** proyectos, experimentos y aprendizajes recientes.
- **Posts / Insights:** publicaciones sobre TI, Cloud, soporte, DevOps, gobierno e inteligencia artificial.
- **Contact:** enlaces para contacto y redes profesionales.

## Temas editoriales

Las publicaciones del sitio están orientadas principalmente a:

- Cloud Computing y servicios de AWS.
- Cloud Operations y soporte técnico.
- Automatización y prácticas operativas.
- Inteligencia artificial aplicada a TI, soporte y operaciones.
- DevOps, herramientas y tecnologías emergentes.
- Gobierno, riesgo, métricas y adopción responsable de AI.
- Experiencias, aprendizajes y opiniones sobre la evolución de la industria tecnológica.

## Estructura del repositorio

```text
.
├── index.html
├── README.md
├── assets/
│   ├── css/
│   ├── js/
│   ├── sass/
│   └── webfonts/
├── images/
├── posts/
│   ├── ai-como-capacidad-operativa-en-ti.md
│   ├── ai-como-capacidad-operativa-en-ti.html
│   ├── kiro-y-kiro-powers-para-soporte-ti.md
│   └── kiro-y-kiro-powers-para-soporte-ti.html
└── templates/
    ├── post-ceo-ai-template.md
    └── post-section-miniport.html
```

## Publicación de posts

Cada publicación puede mantenerse en dos formatos:

- **Markdown (`.md`):** fuente editorial, metadatos, versión larga, versión corta para LinkedIn y fuentes consultadas.
- **HTML (`.html`):** página individual navegable desde el sitio.

La plantilla base para nuevos posts está en:

[templates/post-ceo-ai-template.md](templates/post-ceo-ai-template.md)

## Bitácora de posts publicados

| Fecha | Título | Target | Tags | Formatos |
| --- | --- | --- | --- | --- |
| 2026-09-12 | AI como capacidad operativa en TI: lo que un CEO si deberia medir | CEO, CIO/CTO, Operaciones TI | `#AIParaCEOs`, `#EstrategiaTI`, `#CloudOperations`, `#AIGovernance`, `#RiesgoOperativo` | [Markdown](posts/ai-como-capacidad-operativa-en-ti.md) / [HTML](posts/ai-como-capacidad-operativa-en-ti.html) |
| 2026-09-12 | Kiro y Kiro Powers: salvando el dia un ticket a la vez | Soporte TI, Operaciones TI, DevOps | `#Kiro`, `#SoporteTI`, `#AIForIT`, `#DevOps`, `#Automatizacion` | [Markdown](posts/kiro-y-kiro-powers-para-soporte-ti.md) / [HTML](posts/kiro-y-kiro-powers-para-soporte-ti.html) |

## Flujo recomendado para nuevos posts

1. Crear el borrador desde [templates/post-ceo-ai-template.md](templates/post-ceo-ai-template.md).
2. Guardar la fuente Markdown en `posts/`.
3. Crear la página HTML individual usando el estilo de Miniport.
4. Agregar o actualizar la tarjeta correspondiente en la sección `Posts / Insights` de `index.html`.
5. Registrar la publicación en la bitácora de este README.
6. Validar el HTML antes de publicar.

## Validación local

Como el sitio es estático, se puede validar la estructura HTML con:

```bash
python3 -m html.parser index.html
python3 -m html.parser posts/ai-como-capacidad-operativa-en-ti.html
python3 -m html.parser posts/kiro-y-kiro-powers-para-soporte-ti.html
git diff --check
```

## Tecnologías y recursos

El proyecto utiliza recursos incluidos originalmente con la plantilla Miniport:

- HTML5 / CSS3
- JavaScript / jQuery
- Font Awesome
- Responsive Tools
- Plantilla Miniport de HTML5 UP

## Créditos

Plantilla original:

- **Miniport** - HTML5 UP
- Autor: AJ - [@ajlkn](https://github.com/ajlkn)
- Licencia: Creative Commons Attribution 3.0
- Sitio: [html5up.net](https://html5up.net/)

Otros recursos utilizados por la plantilla original:

- Unsplash
- Font Awesome
- jQuery
- Responsive Tools

## Sitio web

Visita la página en: **[https://ajha.info/](https://ajha.info/)**
