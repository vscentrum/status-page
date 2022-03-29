import datetime
import markdown


NONE_DATE = datetime.datetime.fromisoformat('2030-01-01 00:00:00')
NONE_DATE_STR = 'Unknown'

def select_relevant_incidents(incidents, date=None):
    if date is None:
        date = datetime.datetime.now()
    return incidents[incidents.end_date > date].copy()

def select_planned_maintenance(incidents, date=None):
    if date is None:
        date = datetime.datetime.now()
    return incidents[incidents.start_date > date].copy()

def select_current_incidents(incidents, date=None):
    if date is None:
        date = datetime.datetime.now()
    incidents.end_date.fillna(NONE_DATE, inplace=True)
    return incidents[(incidents.start_date <= date) & (date <= incidents.end_date)].copy()

def format_name(tech_name):
    return tech_name.replace('_', ' ').capitalize()

def format_headers(df):
    df.columns = list(map(format_name, df.columns))

def add_href(input_df):
    df = input_df.copy()
    df['href'] = df['affected'] + '.html#' + df['id']
    df['title'] = '<a href="' + df['href'] + '">' + df['title'] + '</a>'
    return df

def dataframe_to_html_table(input_df, alt_text):
    df = input_df.copy()
    df.loc[:, ['end_date']] = df.end_date.apply(lambda x: str(x) if x < NONE_DATE else NONE_DATE_STR)
    if len(df) == 0:
        return alt_text
    format_headers(df)
    return df.to_html(index=False, escape=False)

def dataframe_to_html_text(input_df, template, alt_text):
    df = input_df.copy()
    df.loc[:, ['end_date']] = df.end_date.apply(lambda x: str(x) if x < NONE_DATE else NONE_DATE_STR)
    if len(df) == 0:
        return alt_text
    incident_texts = []
    for _, row in df.iterrows():
        row['description'] = markdown.markdown(row['content'])
        incident_texts.append(template.format(**row))
    return '\n\n'.join(incident_texts)

def read_template(template_path):
    with open(template_path, 'r') as file:
        return file.read()

def process_template(file_path, build_path, variables):
    tmpl = read_template(file_path)
    with open(build_path, 'w') as out_file:
        print(tmpl.format(**variables), file=out_file)        
