# Supabase Setup Instructions

## 1. Crear Proyecto en Supabase

1. Ve a [https://app.supabase.com](https://app.supabase.com)
2. Crea un nuevo proyecto
3. Guarda las credenciales que te proporciona:
   - **Project URL**: `https://your-project.supabase.co`
   - **Anon Key**: La clave pública (empieza con `eyJ...`)
   - **Service Role Key**: La clave privada (también empieza con `eyJ...`)

## 2. Configurar Storage Bucket

En el dashboard de Supabase:

1. Ve a **Storage** en el menú lateral
2. Crea un nuevo bucket:
   - Name: `brandbastion-files`
   - Public bucket: **NO** (mantenerlo privado)
   - File size limit: 50MB
   - Allowed MIME types: `application/pdf,text/plain,text/csv`

3. Configura las políticas del bucket:

```sql
-- Política para permitir uploads autenticados
CREATE POLICY "Allow authenticated uploads" ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'brandbastion-files');

-- Política para permitir lectura de archivos propios
CREATE POLICY "Allow users to read own files" ON storage.objects
FOR SELECT TO authenticated
USING (bucket_id = 'brandbastion-files' AND auth.uid()::text = (storage.foldername(name))[1]);
```

## 3. Crear Tablas en la Base de Datos

Ve a **SQL Editor** y ejecuta:

```sql
-- Tabla para conversaciones
CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    title TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Tabla para mensajes
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Tabla para archivos procesados
CREATE TABLE processed_files (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    embeddings_created BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Tabla para análisis guardados
CREATE TABLE saved_analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    insights JSONB NOT NULL,
    context_sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Índices para mejorar performance
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_files_conversation ON processed_files(conversation_id);
CREATE INDEX idx_analyses_conversation ON saved_analyses(conversation_id);

-- RLS (Row Level Security)
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_analyses ENABLE ROW LEVEL SECURITY;

-- Políticas RLS básicas (ajustar según necesidades)
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own conversations" ON conversations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view messages in own conversations" ON messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM conversations 
            WHERE conversations.id = messages.conversation_id 
            AND conversations.user_id = auth.uid()
        )
    );
```

## 4. Configurar las Variables de Entorno

Copia el archivo `env.example` a `.env`:

```bash
cp env.example .env
```

Luego edita `.env` con tus credenciales:

```env
# Reemplaza con tus valores reales
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=eyJ...tu-anon-key...
SUPABASE_SERVICE_KEY=eyJ...tu-service-role-key...
```

## 5. Verificar la Conexión

Una vez configurado, puedes verificar la conexión ejecutando:

```bash
python backend/test_supabase_connection.py
```

## Notas Importantes

1. **Seguridad**: Nunca expongas la `SERVICE_KEY` en el frontend
2. **CORS**: Asegúrate de agregar `http://localhost:3000` a los orígenes permitidos en Supabase
3. **Límites**: El plan gratuito tiene límites de almacenamiento (1GB) y transferencia
4. **Backups**: Configura backups automáticos en producción

## Próximos Pasos

Una vez configurado Supabase, la aplicación podrá:
- Guardar PDFs subidos en Storage
- Persistir conversaciones en PostgreSQL
- Cachear embeddings procesados
- Mantener historial de análisis