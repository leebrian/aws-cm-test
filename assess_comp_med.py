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
        print('no raw dat, go get it')
        r = requests.get(
            'https://gitlab.com/gte577z/ml-workshop/raw/master/dat/text.csv?inline=false')
        with open('dat/text.csv', 'w') as file:
            file.write(r.text)

    if not os.path.exists('dat/text-mapped.csv'):
        print('no mapped dat, make it')
        df = pandas.read_csv('dat/text.csv')
        if 'result_file' not in df.columns:
            df['result_file'] = ''
    else:
        df = pandas.read_csv('dat/text-mapped.csv')

    return df


def call_aws(client):
    # aws free tier is limited so I just want to call for every text, save off mapped, and process the results later
    text = load_cc_df()
    print('describe synthetic chief complaint mapping dataframe : \n' +
          text.describe().to_string())
    for i in range(len(text.index)):
        if (pandas.isnull(text.loc[i].result_file)):
            response = client.detect_entities(Text=text.loc[i].text)
            filename = str(i)+'-out.json'
            with open('results/' + filename, 'w') as file:
                json.dump(response, file)
            text.loc[i, 'result_file'] = filename

    # cleanup and write out what has been processed
    text.to_csv('dat/text-mapped.csv', index=False)


def main():
    print('hello world')
    client = boto3.client(service_name='comprehendmedical')
    call_aws(client)

    # todo process mapping
    # todo make sense of it


if __name__ == "__main__":
    main()
