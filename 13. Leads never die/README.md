# Leads never die

## Jane-7710

## Forensics + Webex

## Medium - Hard

### Question Description

A major investigation was stalled when the lead investigator was found dead under suspicious circumstances. On his system, investigators found a single PDF of a personal footnote.
The culprits had seemingly gone to great lengths to conceal their identities,they had deleted most of the other files in his system leaving this irrelevant footnote behind. But the detective was infamous for layering his investigation and hiding clues in unexpected places.
Remember, information lays in the eyes of the beholder

### Files needed

A PDF file
basic hosted suspect list website

### Intended Solution

1. The players first open the pdf to find a random generic message
2. The pdf is essentially a layered vector pdf containing lot of meaningless layered objects and they can find out the id and password either by opening it in a pdf vector software like inkscape or by running a small python code
3. THe players then reach the site with 6 suspects. Three of the suspects contain an extra evidence stating that somethings might be restricted due to their limited access.
4. While investigating the cases, the players notice small clues spread throughout the files: references to things being represented in different ways, old compatibility systems, a Python-related comment,random ramblings about snakes, and a September 2022 security reference. None of the clues alone explains the vulnerability.
5. The players then inspect the site's network traffic and notice that the login session is stored in a cookie called auth_token. They decode the cookie and see a JWT containing normal information such as the investigator ID, role, clearance, and accessible cases.
6. They try changing the clearance or role directly inside the JWT, but the modified token is rejected because the signature no longer matches. This tells them that they cannot simply edit the claims.
7. The September 2022 clue eventually leads them to the Python JWT vulnerability PYSEC-2022-259 / CVE-2022-39227. They discover that the old python-jwt implementation handles JWT/JWS data differently from jwcrypto when compact and JSON forms are mixed.
8. The players use their legitimate JWT to build the malicious token. They keep the original header, original payload, and real signature, then create a second payload containing the higher privileges they want, such as:
role = admin
clearance = 4
CASE-7319 access
9. The players replace the auth_token cookie with this specially constructed token and send the request again. The two token readers now disagree, the authentication parser (jwscrypto) eads the original signed information investigator / clearance 2 but the authorization (python-jwt 3.3.3) splits the raw token at "." and thus reads the forged information as the original claim.
10. The restricted information for the relevant cases is now accessible. The players inspect the newly unlocked information and compare the different clues.
11. Two of the three unlocked files are red herrings and lead nowhere. One points toward the actual incident and identifies CASE-7319 as the important case and on opening that they get the flag.

### Flag

> kernel{c00kie5_alw3y5_l34v3_c7umb5}
