"""Built-in song library (public-domain melodies), in engine.parse_text format.
Token = pitch[:beats]  (default 1 beat = quarter note), r = rest, bars split by |.
"""

SONGS = [
    dict(id="mary", title="Mary Had a Little Lamb", composer="Traditional", tempo=100, ts=(4, 4), key=0, text="""
        E4 D4 C4 D4 | E4 E4 E4:2 | D4 D4 D4:2 | E4 G4 G4:2 |
        E4 D4 C4 D4 | E4 E4 E4 E4 | D4 D4 E4 D4 | C4:4"""),
    dict(id="twinkle", title="Twinkle Twinkle Little Star", composer="Traditional", tempo=100, ts=(4, 4), key=0, text="""
        C4 C4 G4 G4 | A4 A4 G4:2 | F4 F4 E4 E4 | D4 D4 C4:2 |
        G4 G4 F4 F4 | E4 E4 D4:2 | G4 G4 F4 F4 | E4 E4 D4:2 |
        C4 C4 G4 G4 | A4 A4 G4:2 | F4 F4 E4 E4 | D4 D4 C4:2"""),
    dict(id="row", title="Row, Row, Row Your Boat", composer="Traditional", tempo=72, ts=(6, 8), key=0, text="""
        C4:1.5 C4:1.5 | C4:1 D4:0.5 E4:1.5 | E4:1 D4:0.5 E4:1 F4:0.5 | G4:3 |
        C5:0.5 C5:0.5 C5:0.5 G4:0.5 G4:0.5 G4:0.5 | E4:0.5 E4:0.5 E4:0.5 C4:0.5 C4:0.5 C4:0.5 |
        G4:1 F4:0.5 E4:1 D4:0.5 | C4:3"""),
    dict(id="ode", title="Ode to Joy", composer="Ludwig van Beethoven", tempo=110, ts=(4, 4), key=0, text="""
        E4 E4 F4 G4 | G4 F4 E4 D4 | C4 C4 D4 E4 | E4:1.5 D4:0.5 D4:2 |
        E4 E4 F4 G4 | G4 F4 E4 D4 | C4 C4 D4 E4 | D4:1.5 C4:0.5 C4:2"""),
    dict(id="birthday", title="Happy Birthday", composer="Mildred & Patty Hill", tempo=100, ts=(3, 4), key=0, text="""
        r:2 G4:0.75 G4:0.25 | A4 G4 C5 | B4:2 G4:0.75 G4:0.25 | A4 G4 D5 | C5:2 G4:0.75 G4:0.25 |
        G5 E5 C5 | B4 A4 F5:0.75 F5:0.25 | E5 C5 D5 | C5:3"""),
    dict(id="jingle", title="Jingle Bells", composer="James Lord Pierpont", tempo=120, ts=(4, 4), key=0, text="""
        E4 E4 E4:2 | E4 E4 E4:2 | E4 G4 C4:1.5 D4:0.5 | E4:4 |
        F4 F4 F4:1.5 F4:0.5 | F4 E4 E4 E4:0.5 E4:0.5 | E4 D4 D4 E4 | D4:2 G4:2 |
        E4 E4 E4:2 | E4 E4 E4:2 | E4 G4 C4:1.5 D4:0.5 | E4:4 |
        F4 F4 F4 F4 | F4 E4 E4 E4:0.5 E4:0.5 | G4 G4 F4 D4 | C4:4"""),
    dict(id="saints", title="When the Saints Go Marching In", composer="Traditional", tempo=120, ts=(4, 4), key=0, text="""
        r C4 E4 F4 | G4:4 | r C4 E4 F4 | G4:4 | r C4 E4 F4 | G4:2 E4:2 | C4:2 E4:2 | D4:4 |
        r E4 E4 D4 | C4:3 C4 | E4:2 G4 G4 | F4:3 F4 | E4 F4 G4:2 | E4:2 C4:2 | D4:2 D4:2 | C4:4"""),
    dict(id="greensleeves", title="Greensleeves", composer="Traditional (16th c. England)", tempo=96, ts=(3, 4), key=0, text="""
        r:2 A4 | C5:2 D5 | E5:1.5 F5:0.5 E5 | D5:2 B4 | G4:1.5 A4:0.5 B4 | C5:2 A4 | A4:1.5 G#4:0.5 A4 |
        B4:2 G#4 | E4:2 A4 | C5:2 D5 | E5:1.5 F5:0.5 E5 | D5:2 B4 | G4:1.5 A4:0.5 B4 |
        C5:1.5 B4:0.5 A4 | G#4:1.5 F#4:0.5 G#4 | A4:3"""),
    dict(id="minuet", title="Minuet in G", composer="Christian Petzold (attr. J.S. Bach)", tempo=110, ts=(3, 4), key=1, text="""
        D5 G4:0.5 A4:0.5 B4:0.5 C5:0.5 | D5 G4 G4 | E5 C5:0.5 D5:0.5 E5:0.5 F#5:0.5 | G5 G4 G4 |
        C5 D5:0.5 C5:0.5 B4:0.5 A4:0.5 | B4 C5:0.5 B4:0.5 A4:0.5 G4:0.5 | F#4 G4:0.5 A4:0.5 B4:0.5 G4:0.5 | A4:3 |
        D5 G4:0.5 A4:0.5 B4:0.5 C5:0.5 | D5 G4 G4 | E5 C5:0.5 D5:0.5 E5:0.5 F#5:0.5 | G5 G4 G4 |
        C5 D5:0.5 C5:0.5 B4:0.5 A4:0.5 | B4 C5:0.5 B4:0.5 A4:0.5 G4:0.5 | A4 B4:0.5 A4:0.5 G4:0.5 F#4:0.5 | G4:3"""),
    dict(id="canon", title="Canon in D", composer="Johann Pachelbel", tempo=72, ts=(4, 4), key=2, text="""
        F#5:2 E5:2 | D5:2 C#5:2 | B4:2 A4:2 | B4:2 C#5:2 |
        D5 C#5 B4 A4 | G4 F#4 G4 E4 | D4 F#4 A4 G4 | F#4 D4 F#4 E4 |
        D4 B3 D4 A4 | G4 B4 A4 G4 | F#4 D4 E4 C#5 | D5:4"""),
    dict(id="elise", title="Für Elise", composer="Ludwig van Beethoven", tempo=66, ts=(3, 8), key=0, text="""
        r:1 E5:0.25 D#5:0.25 | E5:0.25 D#5:0.25 E5:0.25 B4:0.25 D5:0.25 C5:0.25 |
        A4:0.5 r:0.25 C4:0.25 E4:0.25 A4:0.25 | B4:0.5 r:0.25 E4:0.25 G#4:0.25 B4:0.25 |
        C5:0.5 r:0.25 E4:0.25 E5:0.25 D#5:0.25 | E5:0.25 D#5:0.25 E5:0.25 B4:0.25 D5:0.25 C5:0.25 |
        A4:0.5 r:0.25 C4:0.25 E4:0.25 A4:0.25 | B4:0.5 r:0.25 E4:0.25 C5:0.25 B4:0.25 | A4:1 r:0.5"""),
    dict(id="mountain", title="In the Hall of the Mountain King", composer="Edvard Grieg", tempo=150, ts=(4, 4), key=2, text="""
        B3:0.5 C#4:0.5 D4:0.5 E4:0.5 F#4:0.5 D4:0.5 F#4:1 | F4:0.5 C#4:0.5 F4:1 E4:0.5 C4:0.5 E4:1 |
        B3:0.5 C#4:0.5 D4:0.5 E4:0.5 F#4:0.5 D4:0.5 F#4:0.5 B4:0.5 | A4:0.5 F#4:0.5 D4:0.5 F#4:0.5 A4:2 |
        F#4:0.5 G#4:0.5 A#4:0.5 B4:0.5 C#5:0.5 A#4:0.5 C#5:1 | D5:0.5 A#4:0.5 D5:1 C#5:0.5 A#4:0.5 C#5:1 |
        F#4:0.5 G#4:0.5 A#4:0.5 B4:0.5 C#5:0.5 A#4:0.5 C#5:0.5 F#5:0.5 | E5:0.5 C#5:0.5 A#4:0.5 C#5:0.5 E5:2"""),
    dict(id="turkish", title="Rondo alla Turca (Turkish March)", composer="Wolfgang Amadeus Mozart", tempo=120, ts=(2, 4), key=0, text="""
        B4:0.25 A4:0.25 G#4:0.25 A4:0.25 C5:0.5 r:0.5 | D5:0.25 C5:0.25 B4:0.25 C5:0.25 E5:0.5 r:0.5 |
        F5:0.25 E5:0.25 D#5:0.25 E5:0.25 B5:0.25 A5:0.25 G#5:0.25 A5:0.25 |
        B5:0.25 A5:0.25 G#5:0.25 A5:0.25 C6:1 | A5:0.5 B5:0.5 C6:0.5 B5:0.5 | B5:0.5 A5:0.5 G5:0.5 A5:0.5 |
        B5:0.5 A5:0.5 G5:0.5 A5:0.5 | B5:0.5 A5:0.5 G5:0.5 F#5:0.5 | E5:2"""),
    dict(id="bumblebee", title="Flight of the Bumblebee", composer="Nikolai Rimsky-Korsakov", tempo=144, ts=(4, 4), key=0, text="""
        E5:0.25 D#5:0.25 D5:0.25 C#5:0.25 D5:0.25 C#5:0.25 C5:0.25 B4:0.25 C5:0.25 B4:0.25 A#4:0.25 A4:0.25 G#4:0.25 G4:0.25 F#4:0.25 F4:0.25 |
        E4:0.25 D#4:0.25 D4:0.25 C#4:0.25 D4:0.25 C#4:0.25 C4:0.25 B3:0.25 C4:0.25 B3:0.25 A#3:0.25 A3:0.25 G#3:0.25 G3:0.25 F#3:0.25 F3:0.25 |
        E3:0.25 D#3:0.25 D3:0.25 C#3:0.25 C3:0.25 F3:0.25 E3:0.25 D#3:0.25 E3:0.25 D#3:0.25 D3:0.25 C#3:0.25 C3:0.25 F3:0.25 E3:0.25 D#3:0.25 |
        E3:0.25 D#3:0.25 D3:0.25 C#3:0.25 D3:0.25 C#3:0.25 C3:0.25 B2:0.25 C3:0.25 C#3:0.25 D3:0.25 D#3:0.25 E3:0.25 F3:0.25 E3:0.25 D#3:0.25 |
        E3:4"""),
]
