#!/usr/bin/env python3
"""
Script to import Pokemon summaries from production database to local database.
Usage: python3 import_pokemon_summaries.py --host 149.28.243.132 --database pokeapi --user pokeapi --password "your_password"
"""

import argparse
import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.model import db, Resource

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    load_dotenv(".flaskenv", override=True)

def import_from_production(host, database, user, password, local_port=5432):
    """
    Import Pokemon summaries from production database to local database.
    
    Args:
        host (str): Production database host
        database (str): Database name
        user (str): Database username
        password (str): Database password
        local_port (int): Local port (default 5432 for direct connection, 63333 for SSH tunnel)
    """
    try:
        # Import psycopg2 for direct database connection
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        print(f"Connecting to production database at {host}:{local_port}")
        print(f"Database: {database}, User: {user}")
        print("=" * 60)
        
        # Connect to production database
        prod_conn = psycopg2.connect(
            host=host,
            port=local_port,
            database=database,
            user=user,
            password=password
        )
        prod_cursor = prod_conn.cursor(cursor_factory=RealDictCursor)
        
        print("✓ Connected to production database")
        
        # Query production database for ALL resources (not just pokemon)
        query = """
        SELECT resource, name, summary 
        FROM resources 
        WHERE summary IS NOT NULL 
        AND summary != '' 
        AND summary != 'NaN'
        ORDER BY resource, name;
        """
        
        prod_cursor.execute(query)
        prod_results = prod_cursor.fetchall()
        
        print(f"✓ Found {len(prod_results)} resources with summaries in production")
        
        # Close production connection
        prod_cursor.close()
        prod_conn.close()
        
        # Now work with local database using Flask app context
        app = create_app()
        
        with app.app_context():
            print("✓ Connected to local database")
            
            # Get existing local summaries for comparison
            local_resources = Resource.query.filter(
                Resource.summary.isnot(None),
                Resource.summary != '',
                Resource.summary != 'NaN'
            ).all()
            
            local_summaries = {(r.resource, r.name): r.summary for r in local_resources}
            print(f"✓ Found {len(local_summaries)} existing summaries in local database")
            
            # Process each production summary
            updated_count = 0
            new_count = 0
            unchanged_count = 0
            
            print("\nProcessing summaries...")
            print("=" * 60)
            
            for row in prod_results:
                resource_type = row['resource']
                resource_name = row['name']
                prod_summary = row['summary']
                
                # Check if this resource exists locally
                local_resource = Resource.query.filter_by(
                    resource=resource_type, 
                    name=resource_name
                ).first()
                
                if local_resource:
                    # Update existing resource
                    if local_resource.summary != prod_summary:
                        local_resource.summary = prod_summary
                        updated_count += 1
                        print(f"✓ Updated: {resource_type}/{resource_name}")
                    else:
                        unchanged_count += 1
                        print(f"- Unchanged: {resource_type}/{resource_name}")
                else:
                    # Create new resource
                    new_resource = Resource(
                        resource=resource_type,
                        name=resource_name,
                        summary=prod_summary
                    )
                    db.session.add(new_resource)
                    new_count += 1
                    print(f"+ New: {resource_type}/{resource_name}")
            
            # Commit all changes
            db.session.commit()

            print("\n" + "=" * 60)
            print("IMPORT COMPLETE!")
            print("=" * 60)
            print(f"Total processed: {len(prod_results)}")
            print(f"New summaries: {new_count}")
            print(f"Updated summaries: {updated_count}")
            print(f"Unchanged summaries: {unchanged_count}")
            
            # Verify final count
            final_count = Resource.query.filter(
                Resource.summary.isnot(None),
                Resource.summary != '',
                Resource.summary != 'NaN'
            ).count()
            
            print(f"Final local count: {final_count}")
            
            return True
            
    except ImportError:
        print("Error: psycopg2 is required for database connections.")
        print("Install it with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"Error during import: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Import Pokemon summaries from production database to local database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Direct connection to production
  python3 import_pokemon_summaries.py --host 149.28.243.132 --database pokeapi --user pokeapi --password "your_password"
  
  # Using SSH tunnel (tunnel must be established first)
  ssh -L 63333:localhost:5432 pokeapi@149.28.243.132
  python3 import_pokemon_summaries.py --host localhost --port 63333 --database pokeapi --user pokeapi --password "your_password"
        """
    )
    
    parser.add_argument("--host", required=True, help="Production database host")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--user", required=True, help="Database username")
    parser.add_argument("--password", required=True, help="Database password")
    parser.add_argument("--port", type=int, default=5432, help="Database port (default: 5432)")
    
    args = parser.parse_args()
    
    print("Pokemon Summaries Import Tool")
    print("=" * 60)
    print(f"Target: {args.host}:{args.port}")
    print(f"Database: {args.database}")
    print(f"User: {args.user}")
    print("=" * 60)
    
    # Load environment
    load_environment()
    
    # Import summaries
    success = import_from_production(
        host=args.host,
        database=args.database,
        user=args.user,
        password=args.password,
        local_port=args.port
    )
    
    if success:
        print("\n✓ Import completed successfully!")
    else:
        print("\n✗ Import failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()