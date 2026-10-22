# Marauder's Map

## cipher_muse777

## WebEx

## Easy

## Question description
Hermione has vanished from the map, and something about that doesn't quite add up. Search the castle, follow the hidden passages, and uncover what lies beyond the places you're supposed to see. Not every secret stays buried forever.

### Intended Solution 
- Players are given access to the public Marauder's Map application running on: 
- The application contains a search functionality that searches the database for people.
- A normal search such as: Harry, returns visible people.
- Searching for: Hermione, does not return her because Hermione is marked as hidden in the database using: visible = 0
- The search functionality is vulnerable to SQL Injection because the user's input is directly inserted into the SQL query.
- The vulnerable query is approximately:
```
SELECT ...
FROM people
WHERE p.name LIKE '%<input>%'
AND p.visible = 1
```
- Players can use the payload:
```
%' --
```
- this matches everything, and the visibility condition is commented out, hidden entries such as Hermione become visible.

- After confirming SQL Injection, players can use UNION SELECT to retrieve information from the database.
- The original query returns two columns, so the injected query also uses two columns.
- Players can query SQLite's internal schema table: sqlite_master, using:
```
%' UNION SELECT name, sql FROM sqlite_master WHERE type='table' --
```
- This reveals tables such as:
map_services
map_notes
- The important table is: map_services
- because it contains information about other services in the application.
- Players can query it using:
```
 %' AND 1=0 UNION SELECT hostname, CAST(port AS TEXT) FROM map_services --
```
- which will give the hidden internal service 
- The player cannot normally access this address directly because map-internal exists inside the Docker network.
- However, the public application contains a URL-fetching functionality similar to:
/fetch?url=<URL>
The backend essentially performs:
requests.get(url) using the URL supplied by the player.
- This creates an SSRF vulnerability.
- Players can therefore make the public server request the internal service on their behalf:
```
http://map-internal:5001/
```
- The player cannot directly reach map-internal:5001, but the public server can because both containers are connected to the same Docker network.
- The internal service's root endpoint reveals the available internal routes, including:
/people
/archive
- This is how players discover the internal endpoints rather than having to guess them.
- Players can therefore request:
```
http://map-internal:5001/people
```
and:
```
http://map-internal:5001/archive
```
- The /people endpoint confirms that the internal service contains restricted people information.
- The /archive endpoint requires a secret access phrase.
- Players now return to the SQL Injection vulnerability and investigate the other table discovered earlier:
map_notes
- They can query it using:
```
%' AND 1=0 UNION SELECT 'note', content FROM map_notes -- -
```
- This reveals a note containing the access phrase:
mischief managed
- Players can then combine this information with the SSRF vulnerability.
They request:
```
http://map-internal:5001/archive/room-of-requirement?phrase=mischief%20managed
```
- The correct phrase grants access and reveals the archive entry:
room-of-requirement
- Players can now access the discovered archive entry through SSRF:
/fetch?url=http://map-internal:5001/archive/room-of-requirement
- The internal service returns the flag.

### Flag
kernel{7h3_m4p_r3m3mb3r5_wh4t_y0u_h1d3}

