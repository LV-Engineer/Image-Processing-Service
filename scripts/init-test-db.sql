SELECT 'CREATE DATABASE imgproc_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'imgproc_test')\gexec