import os
import json

from flask import Flask, request, render_template, redirect

import dataset

app = Flask(__name__)

DB_URI = os.getenv('DATAVAULT_URI', 'sqlite:///mydatabase.db')
db = dataset.connect(DB_URI)


def init():
    match_table = db['zz_enrich_match']
    entity_table = db['zz_enrich_entity']
    votes_table = db['zz_enrich_votes']

    match_table.create_column('total_votes', db.types.integer)
    match_table.create_column('yes', db.types.integer)
    match_table.create_column('no', db.types.integer)
    match_table.create_column('maybe', db.types.integer)

    votes_table.create_column('candidate_id', db.types.text)
    votes_table.create_column('user_id', db.types.text)
    votes_table.create_column('vote', db.types.text)
    db.commit()


def get_user_name():
    return request.headers.get("KEYCLOAK_USERNAME") or 'xxx'


def increment_field(data, field):
    if data[field] == None:
        data[field] = 0
    data[field] += 1
    return data


@app.route('/task/', methods=["GET", "POST"])
def task():
    match_table = db['zz_enrich_match']
    entity_table = db['zz_enrich_entity']
    votes_table = db['zz_enrich_votes']
    user_name = get_user_name()
    # Get a candidate with less than 2 votes and one that the current user
    # has not seen yet
    query = """SELECT m.candidate_id, m.entity_id
            FROM zz_enrich_match m
            WHERE (m.total_votes IS Null OR m.total_votes < 2)
            AND NOT EXISTS
            (SELECT * FROM zz_enrich_votes v
            WHERE v.user_id = '{0}'
            AND v.candidate_id = m.candidate_id)
            LIMIT 1""".format(user_name)
    if request.method == 'GET':
        matches = list(db.query(query))
        if matches:
            match = matches[0]
            entity_id = match['entity_id']
            matches = list(match_table.find(entity_id=entity_id))
        else:
            matches = []
        for idx, match in enumerate(matches):
            entity = entity_table.find_one(id=match['candidate_id'])
            if entity:
                match['properties'] = json.loads(entity['properties'])
        ctx = {
            "matches": matches
        }
        return render_template("task.html", **ctx)
    if request.method == 'POST':
        votes = request.form
        for candidate_id in votes:
            with db as tx:
                match_table = tx['zz_enrich_match']
                match = match_table.find_one(candidate_id=candidate_id)
                vote = votes[candidate_id]
                assert vote in ('yes', 'no', 'maybe')
                match = increment_field(match, 'total_votes')
                match = increment_field(match, vote)
                match_table.upsert(match, ['candidate_id'])
                votes_table = tx['zz_enrich_votes']
                votes_table.insert({
                    'candidate_id': candidate_id,
                    'user_id': user_name,
                    'vote': vote,
                })

        return redirect('/task/')

if __name__ == '__main__':
    init()
    app.run()