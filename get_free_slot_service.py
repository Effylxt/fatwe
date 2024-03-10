import streamlit as st
import datetime
import time
import pytz

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title='FatWE: Find A Time Works for Everyone')
st.sidebar.image('fatwelogo.png')
st.title("FatWE")
st.write("(Find A Time Works for Everyone)")
email_markdown = 'Contact: [effyli@google.com](mailto:effyli@google.com)'
st.markdown(email_markdown)

date_range_input = st.date_input("Set date range you want to schedule your meeting", value=[])
meeting_duration_input = st.number_input("Set meeting duration in hours. Must be a multiple of 0.5 hours",
                                         value=0.5,
                                         step=0.5)
attendees_input = st.text_input('Set attendee LDAPs, split by comma. E.g effyli,jiall,dongmao')

if st.button("Submit", type="primary"):
    LDAPS = [attendee.strip() for attendee in attendees_input.split(',')]
    MIN_DATETIME = date_range_input[0]
    MIN_DATETIME = datetime.datetime.combine(MIN_DATETIME, datetime.datetime.min.time())
    MAX_DATETIME = date_range_input[1]
    MAX_DATETIME = datetime.datetime.combine(MAX_DATETIME, datetime.datetime.min.time())

    if MIN_DATETIME == MAX_DATETIME:
        MAX_DATETIME = MAX_DATETIME + datetime.timedelta(days=1)

    DURATION = meeting_duration_input

    time_range_half_hours = int((MAX_DATETIME - MIN_DATETIME).total_seconds() / 1800)

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    min_datetime_str = MIN_DATETIME.isoformat() + 'Z'
    max_datetime_str = MAX_DATETIME.isoformat() + 'Z'
    service = build('calendar', 'v3', credentials=creds)

    free_slots = {}
    all_slots = [i for i in range(time_range_half_hours)]

    for ldap in LDAPS:
        st.write(f'Processing {ldap}')
        email_address = f'{ldap}@google.com'

        while True:
            try:
                events_responses = service.events().list(calendarId=email_address, timeMin=min_datetime_str,
                                                         timeMax=max_datetime_str, singleEvents=True,
                                                         orderBy='updated').execute()
                break
            except HttpError as error:
                print('An error occurred: %s' % error)
                time.sleep(1)

        all_items = events_responses.get('items', [])
        for item in all_items:

            # full day event, ignore it
            if 'date' in item['start']:
                continue

            # accepted meeting or ooo
            if ('dateTime' in item['start'] and item['status'] == 'confirmed') or \
                    'eventType' in item and item['eventType'] == 'outOfOffice':
                start_time = datetime.datetime.strptime(item['start']['dateTime'], '%Y-%m-%dT%H:%M:%S%z') \
                    .astimezone(pytz.utc).replace(tzinfo=None)
                end_time = datetime.datetime.strptime(item['end']['dateTime'], '%Y-%m-%dT%H:%M:%S%z') \
                    .astimezone(pytz.utc).replace(tzinfo=None)

                start_slot = int((start_time - MIN_DATETIME).total_seconds() / 1800)
                end_slot = int((end_time - MIN_DATETIME).total_seconds() / 1800)

                for slot in range(start_slot + 1, end_slot + 1):
                    if slot in all_slots:
                        all_slots.remove(slot)

    all_free_slots = []

    for slot in all_slots:
        duration_slots = int(DURATION / 0.5)
        is_slot_free = True

        for x in range(duration_slots):
            if (slot + x) not in all_slots:
                is_slot_free = False
                break
        if is_slot_free:
            all_free_slots.append(slot)

    st.write('Free slot in UTC timezone:')
    for free_slot in all_free_slots:
        slot_datetime = MIN_DATETIME + datetime.timedelta(seconds=free_slot * 1800)
        st.write(slot_datetime)