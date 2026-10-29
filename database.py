import psycopg2

# შენი საბოლოო და სწორი Supabase კავშირის სტრიქონი
supabase_url = "postgresql://postgres.jmyspsrrrmdhlfmkztku:Shota898163291@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"

try:
    connection = psycopg2.connect(supabase_url)
    print("✅ კავშირი წარმატებით დამყარდა Supabase-ის ბაზასთან!")
    connection.close()
except Exception as error:
    print(f"❌ შეცდომა კავშირისას: {error}")