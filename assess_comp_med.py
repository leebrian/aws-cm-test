#!/usr/local/bin/python

"""

Looking to test out amazon medical comprehend using the list of 40k synthetic chief complaints in Scott's ml-workshop repo...
All the raw responses are dumped out to /results 1:1 from amazon and mapped in text-mapped.csv
TODO DX and other info written out to text-acm.csv (maybe switch this to json)
TODO check the CompMed values against the CCS diagnosis categories

author: brian@prepend.com
date-created: 2018-12-20
"""


import boto3
import os
import requests
import pandas
import json
import numpy
import re


def test_detect_entities(client):
    """ might cost money"""
    result = client.detect_entities(Text='cerealx 84 mg daily')
    entities = result['Entities']
    for entity in entities:
        print('Entity', entity)


def dump_data_map(map):
    map_str = json.dumps(map, indent=4)
    # print(map_str)
    with open('doc/data-map.json', 'w', encoding='utf-8') as file:
        file.write(map_str)


def dump_map_to_reamde(map):
    with open('./readme.md', encoding='utf-8') as file:
        readme = file.read()

    new_readme = re.sub(r'(?is)## Data Maps.+',
                        '## Data Maps\n\n```json\n' + json.dumps(map, indent=4) + '\n```\n', readme)

    # print(new_readme)
    with open('./README.md', 'w', encoding='utf-8') as file:
        file.write(new_readme)


def doc_data_map():
    map = [
        {
            "data-source": "ML-Workshop-Synthetic-Chief-Complaints",
            "data-owner": "https://gitlab.com/gte577z",
            "data-custodian": "https://gitlab.com/gte577z",
            "address": "https://gitlab.com/gte577z/ml-workshop/raw/master/data/text.csv",
            "extract-date": "2018-12-20",
            "format": "CSV",
            "methods": "https://doi.org/10.1038/s41746-018-0070-0",
            "fields": ["text", "diagnosis"]
        },
        {
            "data-source": "AWS-Medical-Comprehend-Assess-Chief-Complaints",
            "data-owner": "OCIO",
            "data-custodian": "OCIO",
            "address": "https://github.com/leebrian/aws-cm-test/blob/master/dat/text-acm.csv",
            "format": "CSV",
            "methods": "https://github.com/leebrian/aws-cm-test",
            "tags": ["AWS", "Comprehend Medical"],
            "fields": ["text", "diagnosis", "aws-text", "aws-score", "aws-category", "aws-category", "aws-trait"],
            "upstream":"ML-Workshop-Synthetic-Chief-Complaints"

        }
    ]

    return map


def load_cc_df():
    if not os.path.isdir('dat'):
        os.mkdir('dat')

    if not os.path.exists('dat/text.csv'):
        print('no raw dat, go get it')
        r = requests.get(
            'https://gitlab.com/gte577z/ml-workshop/raw/master/data/text.csv?inline=false')
        with open('dat/text.csv', 'w', encoding='utf-8') as file:
            file.write(r.text)

    if not os.path.exists('dat/text-mapped.csv'):
        print('no mapped dat, make it')
        df = pandas.read_csv('dat/text.csv')
        if 'result_file' not in df.columns:
            df['result_file'] = ''
    else:
        df = pandas.read_csv('dat/text-mapped.csv',)

    return df


def call_aws(client):
    """ most like to cost money since free tier stops around 25k"""
    # aws free tier is limited so I just want to call for every text, save off mapped, and process the results later
    text = load_cc_df()
    print('describe synthetic chief complaint mapping dataframe : \n' +
          text.describe().to_string())
    for i in range(len(text.index)):
        if (pandas.isnull(text.loc[i].result_file)):
            print('calling aws for ' + str(i) + text.loc[i].text)
            response = client.detect_entities(Text=text.loc[i].text)
            filename = str(i)+'-out.json'
            with open('results/' + filename, 'w', encoding='utf-8') as file:
                json.dump(response, file)
            text.loc[i, 'result_file'] = filename

    # cleanup and write out what has been processed
    text.to_csv('dat/text-mapped.csv', index=False, encoding='utf-8')


def process_acm():
    """
    Limited in that it will only capture the last trait for dx, symptom, or sign. Might want to switch to json because of csv limitation.
    """
    map_df = pandas.read_csv('dat/text-mapped.csv')
    acm_df = pandas.DataFrame(data=map_df.loc[:, ['text', 'diagnosis']], columns=[
        "text",
        "diagnosis",
        "aws-entity-count",
        "aws-dx-count",
        "aws-dx-text",
        "aws-dx-score",
        "aws-dx-category",
        "aws-dx-type",
        "aws-dx-trait-name",
        "aws-dx-trait-score",
        "aws-sy-count",
        "aws-sy-text",
        "aws-sy-score",
        "aws-sy-category",
        "aws-sy-type",
        "aws-sy-trait-name",
        "aws-sy-trait-score",
        "aws-sign-count",
        "aws-sign-text",
        "aws-sign-score",
        "aws-sign-category",
        "aws-sign-type",
        "aws-sign-trait-name",
        "aws-sign-trait-score"
    ])
    assert len(map_df) == len(
        acm_df), 'text mapped and acm text should be same length'
    # print('len map_df ' + str(len(map_df)))
    # print('len acm_df ' + str(len(acm_df)))

    for row in map_df.itertuples():
        with open('results/'+row.result_file, encoding='utf-8') as file:
            result = json.load(file)
            acm_df.loc[row.Index, 'aws-entity-count'] = len(result['Entities'])
            for entity in result['Entities']:
                dx_count = 0
                sym_count = 0
                sign_count = 0
                for trait in entity['Traits']:
                    if trait['Name'] == 'DIAGNOSIS':
                        dx_count += 1
                        acm_df.loc[row.Index, 'aws-dx-text'] = entity['Text']
                        acm_df.loc[row.Index, 'aws-dx-score'] = entity['Score']
                        acm_df.loc[row.Index,
                                   'aws-dx-category'] = entity['Category']
                        acm_df.loc[row.Index, 'aws-dx-type'] = entity['Type']
                        acm_df.loc[row.Index,
                                   'aws-dx-trait-name'] = trait['Name']
                        acm_df.loc[row.Index,
                                   'aws-dx-trait-score'] = trait['Score']
                    elif trait['Name'] == 'SYMPTOM':
                        sym_count += 1
                        acm_df.loc[row.Index, 'aws-sy-text'] = entity['Text']
                        acm_df.loc[row.Index, 'aws-sy-score'] = entity['Score']
                        acm_df.loc[row.Index,
                                   'aws-sy-category'] = entity['Category']
                        acm_df.loc[row.Index, 'aws-sy-type'] = entity['Type']
                        acm_df.loc[row.Index,
                                   'aws-sy-trait-name'] = trait['Name']
                        acm_df.loc[row.Index,
                                   'aws-sy-trait-score'] = trait['Score']
                    elif trait['Name'] == 'SIGN':
                        sign_count += 1
                        acm_df.loc[row.Index, 'aws-sign-text'] = entity['Text']
                        acm_df.loc[row.Index,
                                   'aws-sign-score'] = entity['Score']
                        acm_df.loc[row.Index,
                                   'aws-sign-category'] = entity['Category']
                        acm_df.loc[row.Index, 'aws-sign-type'] = entity['Type']
                        acm_df.loc[row.Index,
                                   'aws-sign-trait-name'] = trait['Name']
                        acm_df.loc[row.Index,
                                   'aws-sign-trait-score'] = trait['Score']

                acm_df.loc[row.Index, 'aws-dx-count'] = dx_count
                acm_df.loc[row.Index, 'aws-sy-count'] = sym_count
                acm_df.loc[row.Index, 'aws-sign-count'] = sign_count

    acm_df['aws-entity-count'] = pandas.to_numeric(
        acm_df['aws-entity-count'], downcast='integer')
    acm_df['aws-dx-count'] = acm_df['aws-dx-count'].fillna(0).astype(int)
    acm_df['aws-sy-count'] = acm_df['aws-sy-count'].fillna(0).astype(int)
    acm_df['aws-sign-count'] = acm_df['aws-sign-count'].fillna(0).astype(int)

    dump_acm_text(acm_df)

    return map_df, acm_df


def what_unique_attribute(df, attribute):
    types = []
    for row in df.itertuples():
        with open('results/'+row.result_file, encoding='utf-8') as file:
            result = json.load(file)
            for entity in result['Entities']:
                if entity[attribute] not in types:
                    types.append(entity[attribute])

    return types


def what_unique_traits(df):
    traits = []
    for row in df.itertuples():
        with open('results/'+row.result_file, encoding='utf-8') as file:
            result = json.load(file)
            for entity in result['Entities']:
                for trait in entity['Traits']:
                    tuple = (entity['Type'], entity['Category'], trait['Name'])
                    if tuple not in traits:
                        traits.append(tuple)

    return traits


def dump_acm_text(df):
    df.to_csv('dat/text-acm.csv', index=False,
              encoding='utf-8')


def doc_acm_text(map, df):
    with open('doc/notes.txt', 'w', encoding='utf-8') as file:

        file.write('Unique types ' + str(what_unique_attribute(map, 'Type')))
        file.write('\nUnique categories ' +
                   str(what_unique_attribute(map, 'Category')))
        file.write('\nUnique trait names ' + str(what_unique_traits(map)))
        file.write('\nacm text dataframe description\n' +
                   df.describe().to_string())

        file.write('\nEntity count frequency distribution\n' +
                   df['aws-entity-count'].value_counts().to_string())
        file.write('\nDiagnosis count frequency distribution\n' +
                   df['aws-dx-count'].value_counts().to_string())
        file.write('\nSymptom count frequency distribution\n' +
                   df['aws-sy-count'].value_counts().to_string())
        file.write('\nSign count frequency distribution\n' +
                   df['aws-sign-count'].value_counts().to_string())


def main():
    print('hello world')

    # housekeeping with docs
    map = doc_data_map()
    dump_data_map(map)
    dump_map_to_reamde(map)

    client = boto3.client(service_name='comprehendmedical')
    call_aws(client)

    # todo process mapping
    map, text = process_acm()

    doc_acm_text(map, text)

    # todo make sense of it


if __name__ == "__main__":
    main()
