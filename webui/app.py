#!/usr/bin/env python
import mysql.connector
from datetime import datetime

from flask import Flask, render_template, request, send_from_directory
app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="besuchertracker"
)

cursor = db.cursor(prepared=True)

get_user_stmt = '''
SELECT * FROM stammdaten s
LEFT JOIN zustandsdaten z
ON s.besucher_id = z.besucher_id
WHERE s.besucher_id = %s
LIMIT 1
'''

insert_status_stmt = 'INSERT INTO zustandsdaten (besucher_id, zustand) VALUES (%s, %s)'
update_status_stmt = 'UPDATE zustandsdaten SET zustand = %s WHERE besucher_id = %s'
check_id_stmt = 'SELECT zustand FROM zustandsdaten WHERE besucher_id = %s LIMIT 1'
track_user_stmt = 'INSERT INTO verlaufsdaten (zeitstempel, besucher_id, aktion) VALUES (%s, %s, %s)'

new_user_stmt = '''
INSERT INTO stammdaten
    (besucher_id, name, adresse1, plz, adresse2,
     telefon, email, status, coronawarn)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
'''

update_user_stmt = '''
UPDATE stammdaten
SET name = %s, adresse1 = %s, plz = %s, adresse2 = %s,
    telefon = %s, email = %s, status = %s,
    coronawarn = %s
WHERE besucher_id = %s
'''

count_user_status_stmt = '''
SELECT
  COUNT(DISTINCT(b.besucher_id)) AS anzahl
  ,IFNULL(z.zustand,"nicht gesehen") AS zustand
  ,IFNULL(s.status,"nicht registriert") AS status
FROM
(SELECT DISTINCT(besucher_id)
 FROM zustandsdaten
 UNION
 SELECT DISTINCT(besucher_id)
 FROM stammdaten) AS b
LEFT JOIN zustandsdaten AS z
ON z.besucher_id = b.besucher_id
LEFT JOIN
  (SELECT besucher_id, status FROM stammdaten) AS s
ON s.besucher_id = b.besucher_id
GROUP BY z.zustand, s.status
ORDER BY s.status, z.zustand
'''

get_tracking_data_stmt = '''
SELECT
zeitstempel, v.besucher_id,
IFNULL(soundex(name), "unbekannt") as alias,
IFNULL(status, "unbekannt") as status,
aktion
FROM verlaufsdaten v
LEFT JOIN
(SELECT name, status, besucher_id FROM stammdaten) as s
on v.besucher_id = s.besucher_id
WHERE
v.besucher_id = IFNULL(%s,v.besucher_id)
ORDER BY zeitstempel DESC
'''

GAST_MAX = 700
CREW_BAND_MAX = 100

@app.route('/stammdaten',methods=['POST','GET'])
def stammdaten():

    if request.method == 'POST':
        # Update entry from form
        besucher_id = request.form.get('besucher_id', default=0, type=int)
        cursor.execute(get_user_stmt, (besucher_id,))
        besucher = cursor.fetchall()

        name = request.form.get('name')
        adresse1 = request.form.get('adresse1')
        plz = request.form.get('plz')
        adresse2 = request.form.get('adresse2')
        telefon = request.form.get('telefon')
        email = request.form.get('email')
        status = request.form.get('status')
        coronawarn = request.form.get('coronawarn', default=0, type=int)
        zustand = request.form.get('zustand')

        if cursor.rowcount == 0:
            print('Adding new user: {}'.format(besucher_id))
            cursor.execute(new_user_stmt, (besucher_id,
                                           name, adresse1, plz, adresse2,
                                           telefon,email,status,coronawarn))
        else:
            print('Updating user {}'.format(besucher_id))
            cursor.execute(update_user_stmt, (name, adresse1, plz, adresse2,
                                              telefon,email,status,coronawarn,
                                              besucher_id))

        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(track_user_stmt, (now, besucher_id, zustand))
        cursor.execute(check_id_stmt, (besucher_id,))
        cursor.fetchall()
        if cursor.rowcount == 0:
            cursor.execute(insert_status_stmt, (besucher_id, zustand,))
        else:
            cursor.execute(update_status_stmt, (zustand, besucher_id,))

        db.commit()
    else:
        besucher_id = request.args.get('besucher_id', default=0, type=int)
        cursor.execute(get_user_stmt, (besucher_id,))
        besucher = cursor.fetchall()
        if cursor.rowcount == 0:
            print('Besucher ID {} existiert nicht.'.format(besucher_id))
            if besucher_id == 0:
                besucher_id = ''
            return render_template('stammdaten.html', id = besucher_id)
        else:
            for b in besucher:
                name = b[1]
                adresse1 = b[2]
                plz = b[3]
                adresse2 = b[4]
                telefon = b[5]
                email = b[6]
                status = b[7]
                coronawarn = b[8]
                zustand = (None, b[10])[ len(b) > 10 ]

                if besucher_id != b[0]:
                    print('Warning: unexpected ID {} in query for {}'.format(
                        b[0], besucher_id))

                print("""
                ID:      {}
                Name:    {}
                Adresse: {}
                         {} {}
                Telefon: {}
                Email:   {}
                Status:  {}
                CoronaWarn: {}
                Zustand: {}
                """.format(besucher_id, name, adresse1, plz, adresse2, telefon,
                           email, status, coronawarn, zustand))

    return render_template('stammdaten.html',
                           id = besucher_id,
                           name = name,
                           adresse1 = adresse1,
                           plz = plz,
                           adresse2 = adresse2,
                           telefon=telefon,
                           email = email,
                           status = status,
                           coronawarn = coronawarn,
                           zustand = zustand)


@app.route('/verlaufsdaten',methods=['GET'])
def verlaufsdaten():
    besucher_id = request.args.get('besucher_id')
    besucher_id = (besucher_id, None)[besucher_id == '']
    cursor.execute(get_tracking_data_stmt, (besucher_id,))
    verlauf = cursor.fetchall()
    return render_template('verlaufsdaten.html',
                           id = besucher_id,
                           verlauf = verlauf)


@app.route('/',methods=['GET'])
def main():
    cursor.execute(count_user_status_stmt)
    counts = cursor.fetchall()
    anwesend = sum((0,anzahl)[zustand == 'kommt' ] for anzahl, zustand, status in counts)
    anwesend_gast = sum((0,anzahl)[status == 'gast' and
                                   zustand == 'kommt'] for
                        anzahl, zustand, status in counts)
    anwesend_crew_band = sum((0,anzahl)[(status == 'crew' or
                                         status == 'band') and
                                   zustand == 'kommt'] for
                        anzahl, zustand, status in counts)
    abwesend = sum((0,anzahl)[zustand == 'geht' or
                              zustand == 'reserviert'] for
                   anzahl, zustand, status in counts)
    abwesend_gast = sum((0,anzahl)[status == 'gast' and
                                   (zustand == 'geht' or
                                    zustand == 'reserviert')] for
                        anzahl, zustand, status in counts)
    abwesend_crew_band = sum((0,anzahl)[((status == 'crew' or
                                         status == 'band') and
                                   (zustand == 'geht' or
                                    zustand == 'reserviert'))] for
                        anzahl, zustand, status in counts)
    reserviert_gast = sum((0,anzahl)[zustand == 'reserviert' and
                                (status == 'gast' or
                                 status == 'nicht registriert') ] for
                     anzahl, zustand, status in counts)
    reserviert_crew_band = sum((0,anzahl)[zustand == 'reserviert' and
                                (status == 'gast' or
                                 status == 'nicht registriert') ] for
                     anzahl, zustand, status in counts)
    registriert = sum((0,anzahl)[status != 'nicht registriert'] for
                      anzahl, zustand, status in counts)

    return render_template('index.html',
                           counts = counts,
                           registriert = registriert,
                           anwesend = anwesend,
                           anwesend_gast = anwesend_gast,
                           anwesend_crew_band = anwesend_crew_band,
                           reserviert_gast = reserviert_gast,
                           reserviert_crew_band = reserviert_crew_band,
                           abwesend = abwesend,
                           abwesend_gast = abwesend_gast,
                           abwesend_crew_band = abwesend_crew_band,
                           gast_max = GAST_MAX,
                           crew_band_max = CREW_BAND_MAX)

if __name__ == '__main__':
    app.run()
