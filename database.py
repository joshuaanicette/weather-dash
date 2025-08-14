import sqlite3

def init_db():
    """Initialize the SQLite database for storing cities."""
    conn = sqlite3.connect('saved_cities.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cities
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    conn.commit()
    conn.close()

def add_city(city):
    """Add a city to the database if it doesn't already exist."""
    conn = sqlite3.connect('saved_cities.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO cities (name) VALUES (?)", (city.lower(),))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error adding city: {e}")
        return False
    finally:
        conn.close()

def get_cities():
    """Retrieve all saved cities from the database."""
    conn = sqlite3.connect('saved_cities.db')
    c = conn.cursor()
    c.execute("SELECT name FROM cities")
    cities = [row[0] for row in c.fetchall()]
    conn.close()
    return cities

def delete_city(city):
    """Delete a city from the database."""
    conn = sqlite3.connect('saved_cities.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM cities WHERE name = ?", (city.lower(),))
        conn.commit()
        return c.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting city: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized with cities table.")