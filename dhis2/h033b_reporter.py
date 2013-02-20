#!/usr/bin/env python
from django.template import Context, Template
from django.template.loader import get_template
import urllib2, base64
from mtrack.models import XFormSubmissionExtras
from rapidsms_xforms.models import XFormSubmissionValue, XForm, XFormSubmission
from dhis2.models import Dhis2_Mtrac_Indicators_Mapping
from datetime import timedelta

HMIS033B_REPORT_XML_TEMPLATE = "h033b_reporter.xml"
HMIS_033B_PERIOD_ID = u'%dW%d'

class H033B_Reporter(object):
  URL     = "http://dhis/api/dataValueSets"
  HEADERS = {
      'Content-type': 'application/xml',
      'Authorization': 'Basic ' + base64.b64encode("api:P@ssw0rd")
  }

  @classmethod
  def send(self, data):
    request = urllib2.Request(self.URL, data = data, headers = self.HEADERS)
    request.get_method = lambda: "POST"
    return urllib2.urlopen(request)

  @classmethod
  def submit(self, data):
    return self.send(self.generate_xml_report(data))
  
  @classmethod 
  def generate_xml_report(self,data):
    template = get_template(HMIS033B_REPORT_XML_TEMPLATE)
    data = template.render(Context(data))
    return data
    
  @classmethod
  def get_reports_data_for_submission(self,submission_arg):
    submission_extras_list = XFormSubmissionExtras.objects.filter(submission=submission_arg)
    if submission_extras_list : 
      submission_extras = submission_extras_list[0]
      data = {}
      data['orgUnit']         = submission_extras.facility.uuid
      data['completeDate']    = submission_arg.created 
      data['dataValues']      = []

      submission_values = XFormSubmissionValue.objects.filter(submission=submission_arg)
      for submission_value in submission_values : 
        dataValue = self.get_data_values_for_submission(submission_value)
        if dataValue :
          data['dataValues'].append(dataValue)
      return data
    return None
    
  @classmethod
  def get_data_values_for_submission(self, submission_value):
    data_value = {}
    attrib_id = submission_value.attribute_id
    dhis2_mapping = Dhis2_Mtrac_Indicators_Mapping.objects.filter(mtrac_id=attrib_id)
    if dhis2_mapping:
      element_id = dhis2_mapping[0].dhis2_uuid
      combo_id = dhis2_mapping[0].dhis2_combo_id
      data_value['dataElement'] = element_id
      data_value['value'] = submission_value.value
      data_value['categoryOptionCombo']  =combo_id
    return data_value
    
  @classmethod
  def get_submissions_in_date_range(self,from_date,to_date):
    return XFormSubmission.objects.filter(created__range=[from_date, to_date])
    
  @classmethod
  def process_reports_for_last_week(self, date):
    last_monday = self.get_last_sunday(date) + timedelta(days=1)
    submissions_for_last_week = self.get_submissions_in_date_range(last_monday, date)
    return self.get_reports_data_for_submission(submissions_for_last_week)  

  @classmethod  
  def get_week_period_id_for_sunday(self, date):
    year  = date.year
    weekday =  int(date.strftime("%W")) + 1
    return HMIS_033B_PERIOD_ID%(year,weekday) 
    
  @classmethod
  def get_last_sunday(self, date):
    offset_from_last_sunday = date.weekday()+1 
    last_sunday = date  - timedelta(days= offset_from_last_sunday)
    return last_sunday  
    
  @classmethod
  def get_period_id_for_submission(self,date):
    return self.get_week_period_id_for_sunday(self.get_last_sunday(date))   