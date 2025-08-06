# 🚀 Guía de Inicio Rápido - BrandBastion Analytics

## Prerrequisitos
- ✅ Docker y Docker Compose instalados
- ✅ Archivo `.env` configurado con credenciales
- ✅ Proyecto Supabase creado

## Paso 1: Configurar Supabase (Primera vez)

### 1.1 Crear las tablas en Supabase
1. Ve a tu proyecto en [https://app.supabase.com](https://app.supabase.com)
2. Ve a **SQL Editor**
3. Copia y ejecuta todo el SQL de `SUPABASE_SETUP.md` (sección 3)
4. Verifica que se crearon las tablas:
   - `conversations`
   - `messages`
   - `processed_files`
   - `saved_analyses`

### 1.2 Configurar Storage
1. Ve a **Storage** en Supabase
2. Crea el bucket `brandbastion-files` si no existe
3. Configura las políticas del bucket (están en el SQL)

## Paso 2: Construir y Levantar los Servicios

```bash
# 1. Construir todos los contenedores
docker-compose build

# 2. Levantar todos los servicios
docker-compose up -d

# 3. Verificar que todos estén corriendo
docker-compose ps
```

Deberías ver:
- `brandbastion-frontend` en puerto 3000
- `brandbastion-backend` en puerto 8000
- `brandbastion-data-pipeline`
- `brandbastion-redis`

## Paso 3: Crear la Base de Datos Vectorial (FAISS)

### Opción A: Usar los datos de ejemplo incluidos
```bash
# Procesar los PDFs y comentarios de ejemplo
docker exec -it brandbastion-data-pipeline python /app/scripts/process_data.py \
  --pdf-dir /app/data/raw/pdfs \
  --comments-dir /app/data/raw/comments \
  --index-name brandbastion
```

### Opción B: Procesar tus propios datos
```bash
# Si tienes tus propios PDFs/comentarios, cópialos primero:
# cp tus-pdfs/*.pdf data/raw/pdfs/
# cp tus-comentarios.txt data/raw/comments/

# Luego procesa:
docker exec -it brandbastion-data-pipeline python /app/scripts/process_data.py \
  --pdf-dir /app/data/raw/pdfs \
  --comments-dir /app/data/raw/comments \
  --index-name brandbastion
```

Verás output como:
```
Processing PDFs from /app/data/raw/pdfs...
Found 9 PDF files
Processing chart1.pdf...
Creating embeddings for X PDF text chunks...
Processing comments from /app/data/raw/comments...
Creating embeddings for Y comments...
✓ Processing complete!
```

## Paso 4: Verificar la Integración

### 4.1 Test de Supabase
```bash
docker exec -it brandbastion-backend python test_supabase_connection.py
```

Deberías ver:
```
✅ Connection successful!
✅ Conversation created
✅ Messages added
...
```

### 4.2 Verificar la API
```bash
# Check health endpoint
curl http://localhost:8000/health

# Debería retornar:
# {"status":"healthy","supabase_connected":true}
```

## Paso 5: Usar la Aplicación

1. **Abre el navegador**: http://localhost:3000

2. **Prueba con queries del challenge**:
   - "Give me an overview of the points where we're doing worse than in the last reporting period"
   - "What are people so mad about that we have so many negative comments?"
   - "What are the key performance metrics?"

3. **Funcionalidades disponibles**:
   - ✅ Upload de PDFs (drag & drop)
   - ✅ Pegar comentarios directamente
   - ✅ Ver insights en cards visuales
   - ✅ Preguntas sugeridas clickeables
   - ✅ Historial persistente en Supabase

## Paso 6: Monitorear y Debuggear

### Ver logs en tiempo real
```bash
# Todos los servicios
docker-compose logs -f

# Solo backend
docker-compose logs -f backend

# Solo frontend
docker-compose logs -f frontend
```

### Acceder a los contenedores
```bash
# Backend shell
docker exec -it brandbastion-backend bash

# Ver índices FAISS creados
docker exec -it brandbastion-backend ls -la /app/vector-db/indices/
```

### Ver datos en Supabase
1. Ve a tu proyecto en Supabase
2. Ve a **Table Editor**
3. Revisa las tablas:
   - `conversations` - Todas las conversaciones
   - `messages` - Historial de mensajes
   - `saved_analyses` - Insights guardados

## Troubleshooting

### Si los índices FAISS no se crean:
```bash
# Verificar que existan los datos
docker exec -it brandbastion-backend ls -la /app/data/raw/

# Recrear índices manualmente
docker exec -it brandbastion-backend python -c "
from agents.analytics_agent import AnalyticsAgent
agent = AnalyticsAgent()
# Procesar algunos datos de ejemplo
agent.create_indices_from_data(
    charts=['Monthly report: 45% increase in engagement'],
    comments=['Great service!', 'Love the new features']
)
print('✓ Test indices created')
"
```

### Si Supabase no conecta:
1. Verifica las credenciales en `.env`
2. Verifica que las tablas estén creadas
3. Revisa los logs: `docker-compose logs backend | grep -i supabase`

### Si el frontend no carga:
1. Verifica que el backend esté corriendo: `curl http://localhost:8000`
2. Revisa CORS en los logs
3. Limpia cache del navegador

## Comandos Útiles

```bash
# Detener todo
docker-compose down

# Detener y limpiar volúmenes
docker-compose down -v

# Reconstruir un servicio específico
docker-compose build backend

# Ver estado de los servicios
docker-compose ps

# Ejecutar comandos en contenedores
docker exec -it brandbastion-backend python script.py
```

## 🎉 ¡Listo!

La aplicación está corriendo con:
- ✅ Frontend en http://localhost:3000
- ✅ API docs en http://localhost:8000/docs
- ✅ Base de datos vectorial FAISS cargada
- ✅ Persistencia en Supabase activa
- ✅ Análisis avanzado funcionando

¡Ya puedes empezar a analizar datos!