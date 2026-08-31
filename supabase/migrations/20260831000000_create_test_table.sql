create table if not exists test_table (
    id uuid primary key default gen_random_uuid(),
    name text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);


    