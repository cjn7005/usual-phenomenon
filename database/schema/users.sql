CREATE TABLE IF NOT EXISTS users (
	id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
	username VARCHAR(40) NOT NULL 
);
