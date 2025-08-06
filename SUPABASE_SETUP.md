# Supabase Setup Instructions

## 1. Create Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Create a new project
3. Save the credentials provided:
   - **Project URL**: `https://your-project.supabase.co`
   - **Anon Key**: The public key (starts with `eyJ...`)
   - **Service Role Key**: The private key (also starts with `eyJ...`)

## 2. Configure Storage Bucket

In the Supabase dashboard:

1. Go to **Storage** in the sidebar
2. Create a new bucket:
   - Name: `brandbastion-files`
   - Public bucket: **YES** (for challenge simplicity)
   - File size limit: 50MB
   - Allowed MIME types: `application/pdf,text/plain,text/csv`

3. Configure bucket policy for public access:

```sql
-- Policy to allow public uploads (for challenge demo)
CREATE POLICY "Allow public uploads" ON storage.objects
FOR INSERT TO public
WITH CHECK (bucket_id = 'brandbastion-files');

-- Policy to allow public read access
CREATE POLICY "Allow public read" ON storage.objects
FOR SELECT TO public
USING (bucket_id = 'brandbastion-files');
```

## 3. Create Database Tables

Go to **SQL Editor** and execute:

```sql
-- Table for conversations
CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    title TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Table for messages
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Table for processed files
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

-- Table for saved analyses
CREATE TABLE saved_analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    insights JSONB NOT NULL,
    context_sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Indexes for better performance
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_files_conversation ON processed_files(conversation_id);
CREATE INDEX idx_analyses_conversation ON saved_analyses(conversation_id);

-- Disable RLS for challenge simplicity (no authentication)
-- In production, you should enable RLS and create proper policies
```

## 4. Configure Environment Variables

Copy the `env.example` file to `.env`:

```bash
cp env.example .env
```

Then edit `.env` with your credentials:

```env
# Replace with your actual values
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...your-anon-key...
SUPABASE_SERVICE_KEY=eyJ...your-service-role-key...
SUPABASE_STORAGE_BUCKET=brandbastion-files
```

## 5. Verify Connection

Once configured, you can verify the connection by running:

```bash
docker exec -it brandbastion-backend-1 python -c "
import os
from supabase import create_client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)
print('✅ Supabase connection successful!')
"
```

## Important Notes

1. **Security**: This setup is simplified for the challenge. In production:
   - Enable Row Level Security (RLS)
   - Implement proper authentication
   - Use private buckets with authenticated access
2. **CORS**: Make sure to add `http://localhost:3000` to allowed origins in Supabase
3. **Limits**: Free tier has storage (1GB) and transfer limits
4. **Backups**: Configure automatic backups for production

## What This Enables

Once Supabase is configured, the application will:
- Store uploaded PDFs in Supabase Storage
- Persist conversations in PostgreSQL
- Cache processed embeddings
- Maintain analysis history
- Enable data persistence across sessions