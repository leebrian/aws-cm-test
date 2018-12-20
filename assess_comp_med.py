import boto3
import os
import requests
import pandas
import json


def test_detect_entities(client):
    result = client.detect_entities(Text='cerealx 84 mg daily')
    entities = result['Entities']
    for entity in entities:
        print('Entity', entity)


def load_cc_df():
    if not os.path.isdir('dat'):
        os.mkdir('dat')

    if not os.path.exists('dat/text.csv'):
        r = requests.get(
            'https://gitlab.com/gte577z/ml-workshop/raw/master/dat/text.csv?inline=false')
        with open('dat/text.csv', 'w') as file:
            file.write(r.text)
        print('no dat')

    df = pandas.read_csv('dat/text.csv')

    if 'result_file' not in df.columns:
        df['result_file'] = ''

    return df

# aws free tier is limited so I just want to call for every text and map the results


def call_aws(client):
    text = load_cc_df()
    print(text.describe())
    for i in range(10000):
        if (pandas.isnull(text.loc[i].result_file)):
            response = client.detect_entities(Text=text.loc[i].text)
            filename = str(i)+'-out.json'
            with open('results/' + filename, 'w') as file:
                json.dump(response, file)
            text.loc[i, 'result_file'] = filename

    # cleanup and write out what has been processed
    text.to_csv('dat/text.csv', index=False)


def main():
    print('hello world')
    client = boto3.client(service_name='comprehendmedical')
    call_aws(client)


if __name__ == "__main__":
    main()
