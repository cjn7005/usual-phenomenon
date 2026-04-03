CREATE TABLE IF NOT EXISTS sessions (
	id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
	session_key UUID  
);
