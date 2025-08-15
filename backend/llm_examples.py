class LLMExamples:
  example_2_1 = [
    {
        "role": "user",
        "content": """\
<job_description>
About the job

Job Summary

The Lead BI Analyst serves as a partner to the business or clinical area supported and will use analytic expertise including knowledge of data structures, programming, and statistics along with critical thinking and an understanding of their assigned subject area/business to help the organization make data-driven decisions. The Lead BI Analyst makes significant contributions to the organization by collecting, cleaning, and interpreting data sets to answer a questions or solve a problem including identifying and effectively communicating improvement opportunities and supporting the evaluation of existing processes and strategic improvement efforts. Lead BI Analysts consistently act, independently, as the analytics expert in meetings and discussions with their stakeholders while also provide guidance and strategic vision during the full analysis. Must be highly articulate in both oral and written communications, including presentations with the ability to translate analyses and opportunity insights to non-technical stakeholders. Lead BI Analysts must exhibit diplomacy, tact, initiative, and organizational skills, as well as possess the ability to inspire trust and confidence to maintain outstanding customer relationships. Lead Bi Analysts mentor junior BI developers by offering project feedback, participating in code reviews, and providing training in areas of expertise.

Job Duties

    Independently consults with stakeholders to gather project requirements and define scope on projects of all sizes including those that are system-wide, highly visible, and of strategic importance.
    Collaborates with stakeholders in the design and development of analytic studies and reporting solutions to support business needs.
    Plans projects and request completion tasks. 
    Provides time and effort estimates based on requirements gathering. Strong experience independently managing multiple projects is also required. 
    Demonstrates working knowledge of relevant source systems needed to support primary stakeholders and proficiency with related databases/data marts within first year in role. Must stay abreast of current industry trends and become facile with the various business intelligence software systems used at Geisinger.
    Leads the development of analysis approach and reporting needed based on business questions, requirements, and initial analysis findings.
    Develops, validates, and executes complex queries to complete sophisticated data analysis resulting in reports that answers very challenging business questions. Interprets results and makes recommendations to business areas based on findings. Leads efforts when multiple analysts involved.
    Cleary presents analysis and reports to internal customers and stakeholders. Mentors junior analysts by demonstrating how to create engaging presentations and presenting in front of various audiences.
    Routinely uses statistical methods during analyses and considers how best to visualize data that accurately reflects the intended message including the limitations.
    Reports and helps troubleshoot data quality issues when performing data profiling, testing, or validation.
    Collaborative and eager to share knowledge with team members.
    Responsible for participating in and advising strategic departmental initiatives.
    Actively seeks out opportunities to mentor more junior analysts and aid in the development of training.
     May participate in and/or lead industry advisory and/or user groups.
    Strong attention to detail and the ability to be precise and clear when describing results of data analyses.
    Shares important and relevant information with the team. Proactively offers suggestions, provides resources, volunteers for assignments, and removes barriers to help the team accomplish its goals.
    Follows all department"s policies and procedures including request intake/fulfillment, change management, and data governance practices.

Work is typically performed in an office environment. Accountable for satisfying all job specific obligations and complying with all organization policies and procedures. The specific statements in this profile are not intended to be all-inclusive. They represent typical elements considered necessary to successfully perform the job. *Relevant experience may be a combination of related work experience and degree obtained (Associate’s Degree = 2 years; Bachelor’s Degree = 4 years, Master"s Degree = 6 years).

Position Details

Highly Preferred

    Epic Healthy Planet/ Compass Rose, SQL, Epic Clarity/Caboodle 

Education

High School Diploma or Equivalent (GED)- (Required)

Experience

Minimum of 10 years-Relevant experience* (Required)

Certification(s) and License(s)

OUR PURPOSE & VALUES: Everything we do is about caring for our patients, our members, our students, our Geisinger family and our communities. KINDNESS: We strive to treat everyone as we would hope to be treated ourselves. EXCELLENCE: We treasure colleagues who humbly strive for excellence. LEARNING: We share our knowledge with the best and brightest to better prepare the caregivers for tomorrow. INNOVATION: We constantly seek new and better ways to care for our patients, our members, our community, and the nation. SAFETY: We provide a safe environment for our patients and members and the Geisinger family We offer healthcare benefits for full time and part time positions from day one, including vision, dental and domestic partners. Perhaps just as important, from senior management on down, we encourage an atmosphere of collaboration, cooperation and collegiality. We know that a diverse workforce with unique experiences and backgrounds makes our team stronger. Our patients, members and community come from a wide variety of backgrounds, and it takes a diverse workforce to make better health easier for all. We are proud to be an affirmative action, equal opportunity employer and all qualified applicants will receive consideration for employment regardless to race, color, religion, sex, sexual orientation, gender identity, national origin, disability or status as a protected veteran.
</job_description>"""
    },
    {
        "role": "assistant",
        "content": """\
{
  "tagged_list": [
    {
      "raw_string": "High School Diploma or Equivalent (GED)",
      "category": "required"
    },
    {
      "raw_string": "Minimum of 10 years-Relevant experience*",
      "category": "required"
    },
    {
      "raw_string": "Epic Healthy Planet/ Compass Rose",
      "category": "additional"
    },
    {
      "raw_string": "SQL",
      "category": "additional"
    },
    {
      "raw_string": "Epic Clarity/Caboodle",
      "category": "additional"
    }
  ]
}"""
    },
    {
      "role": "user",
      "content": """\
<job_description>
## About the job

Maven is looking for a Senior Manager, Business Intelligence to lead and expand our Business Intelligence function. This role will set the technical vision, manage a growing team, and oversee strategic projects to uncover business insights that enable data-driven decision-making. As part of the Business Intelligence team, you will partner closely with our Client Success, Finance, Sales, and Marketing teams to drive the adoption of scalable data models, reporting solutions, and actionable insights across the organization. As a Senior Manager, Business Intelligence at Maven, you will: Lead, mentor, and develop a high-performing Business Intelligence team, fostering growth and collaboration. Design, develop, and oversee the implementation of data structures from both internal and 3rd party sources for use in analytics and reporting (primarily using SQL and Python). Partner with stakeholders across Client Success, Finance, Sales, Marketing and Engineering teams to build dedicated data models and reporting that support critical business processes and goals. Drive operational efficiency by identifying areas for process improvement and recommending highly scalable solutions. Establish and promote development best practices, coding standards, and design principles across the team. Deliver actionable insights and analysis to stakeholders across Maven teams, highlighting opportunities to improve outcomes and better serve our business. Explore and evaluate emerging technologies, tools, and trends that can drive innovation and improve the efficiency and effectiveness of our data analytics processes. Requirements include 10+ years of relevant analytics or data science experience, including a minimum of 3 years of management experience leading technical teams. Fluency in SQL and a strong background in data visualization. Hands-on experience with Python or R is preferred. Proven ability to manage both long-term strategic initiatives and ad hoc, high-priority requests as needed. Excellent leadership, collaboration, and communication skills, with a track record of working effectively with cross-functional teams and developing junior team members. Maven embraces a flexible hybrid work model with primary operation from New York Metropolitan area, NY, San Francisco/Bay Area, CA, Seattle, WA, Boston, MA, Chicago, IL, and Washington, D.C. The policy balances remote work flexibility with face-to-face interaction benefits.
</job_description>"""
    },
    {
      "role": "assistant",
      "content": """\
{
  "tagged_list": [
    {
      "raw_string": "10+ years of relevant analytics or data science experience, including a minimum of 3 years of management experience leading technical teams.",
      "category": "required"
    },
    {
      "raw_string": "Fluency in SQL and a strong background in data visualization.",
      "category": "required"
    },
    {
      "raw_string": "Hands-on experience with Python or R is preferred.",
      "category": "additional"
    },
    {
      "raw_string": "Proven ability to manage both long-term strategic initiatives and ad hoc, high-priority requests as needed.",
      "category": "required"
    },
    {
      "raw_string": "Excellent leadership, collaboration, and communication skills, with a track record of working effectively with cross-functional teams and developing junior team members.",
      "category": "required"
    }
  ]
}"""
    }
]

  example_2_2 = [
    {"role": "user", "content": """\
<tagged_list>
[
    {"raw_string": "5+ years of experience with SQL and data modeling.", "category": "required"},
    {"raw_string": "Experience with Python.", "category": "additional"},
    {"raw_string": "Fluent in English or Spanish", "category": "required"},
    {"raw_string": "4+ years of financial modeling, with 2+ years doing so in Excel", "category": "required"
]
</tagged_list>"""},
    {"role": "assistant", "content": """\
{
  "atomic_objects": [
    {"requirement_string": "5+ years of experience with SQL", "category": "required"},
    {"requirement_string": "5+ years of experience with data modeling", "category": "required"},
    {"requirement_string": "Experience with Python", "category": "additional"},
    {"requirement_string": "Fluent in English or Spanish", "category": "required"},
    {"requirement_string": "4+ years of financial modeling", "category": "required"},
    {"requirement_string": "2+ years financial modeling in Excel", "category": "required"}
  ]
}
  ]
}"""
    }
]

  example_2_3 = [
    {"role": "user", "content": """\
{"atomic_objects": [{"requirement_string": "Strong communication skills", "category": "required"}, {"requirement_string": "Experience with Python", "category": "additional"}, {"requirement_string": "5+ years of experience with SQL", "category": "required"}]}"""},
    {"role": "assistant", "content": """\
{"classified_objects": [{"requirement_string": "Strong communication skills", "classification": "evaluated_qualification"}, {"requirement_string": "Experience with Python", "classification": "additional_qualification"}, {"requirement_string": "5+ years of experience with SQL", "classification": "required_qualification"}]}"""}
]

  example_3_1 = [
    {"role": "user", "content": """\
<candidate_profile>
"{\n  \"certifications\": [\n    \"Mastering LLMs For Developers & Data Scientists\"\n  ],\n  \"detailed_skills\": [\n    {\n      \"skill\": \"SQL\",\n      \"years_experience\": 7\n    },\n    {\n      \"skill\": \"Process Optimization & Automation\",\n      \"years_experience\": 9\n    },\n    {\n      \"skill\": \"Cross-Functional Collaboration\",\n      \"years_experience\": 11.4\n    },\n    {\n      \"skill\": \"Stakeholder Management\",\n      \"years_experience\": 8.2\n    },\n    {\n      \"skill\": \"Leadership\",\n      \"years_experience\": 8.2\n    },\n    {\n      \"skill\": \"eCommerce Operations\",\n      \"years_experience\": 8.2\n    },\n    {\n      \"skill\": \"Data Analysis\",\n      \"years_experience\": 8.2\n    },\n    {\n      \"skill\": \"Reporting & Dashboarding\",\n      \"years_experience\": 7.2\n    },\n    {\n      \"skill\": \"Predictive Models\",\n      \"years_experience\": 7.2\n    },\n    {\n      \"skill\": \"Cost Reduction\",\n      \"years_experience\": 7\n    },\n    {\n      \"skill\": \"Manpower Planning\",\n      \"years_experience\": 6.1\n    },\n    {\n      \"skill\": \"BigQuery\",\n      \"years_experience\": 5\n    },\n    {\n      \"skill\": \"Metabase\",\n      \"years_experience\": 5\n    },\n    {\n      \"skill\": \"Looker Studio\",\n      \"years_experience\": 5\n    },\n    {\n      \"skill\": \"Data Modeling\",\n      \"years_experience\": 5\n    },\n    {\n      \"skill\": \"Budgeting\",\n      \"years_experience\": 4.3\n    },\n    {\n      \"skill\": \"Data Migration\",\n      \"years_experience\": 4.2\n    },\n    {\n      \"skill\": \"Inventory Control\",\n      \"years_experience\": 4\n    },\n    {\n      \"skill\": \"Supply Chain Management\",\n      \"years_experience\": 4\n    },\n    {\n      \"skill\": \"Production Planning\",\n      \"years_experience\": 3.2\n    },\n    {\n      \"skill\": \"Feasibility Studies\",\n      \"years_experience\": 3.2\n    },\n    {\n      \"skill\": \"Demand Planning\",\n      \"years_experience\": 3\n    },\n    {\n      \"skill\": \"Supply Planning\",\n      \"years_experience\": 3\n    },\n    {\n      \"skill\": \"Integrated Business Planning (IBP)\",\n      \"years_experience\": 3\n    },\n    {\n      \"skill\": \"Project Management\",\n      \"years_experience\": 3\n    },\n    {\n      \"skill\": \"ERP Systems (SAP)\",\n      \"years_experience\": 2.9\n    },\n    {\n      \"skill\": \"Logistics\",\n      \"years_experience\": 2.9\n    },\n    {\n      \"skill\": \"Data Pipeline\",\n      \"years_experience\": 2.9\n    },\n    {\n      \"skill\": \"Warehouse Analytics\",\n      \"years_experience\": 2.9\n    },\n    {\n      \"skill\": \"Data Governance\",\n      \"years_experience\": 2.9\n    },\n    {\n      \"skill\": \"Waste Reduction\",\n      \"years_experience\": 2.9\n    },\n    {\n      \"skill\": \"Python\",\n      \"years_experience\": 2\n    },\n    {\n      \"skill\": \"Pricing Optimization\",\n      \"years_experience\": 1.1\n    },\n    {\n      \"skill\": \"Market Analysis\",\n      \"years_experience\": 1\n    },\n    {\n      \"skill\": \"Microsoft Power BI\",\n      \"years_experience\": 1\n    },\n    {\n      \"skill\": \"Cursor\",\n      \"years_experience\": 1\n    },\n    {\n      \"skill\": \"GitHub Copilot\",\n      \"years_experience\": 1\n    }\n  ],\n  \"domain_specific_experience\": [\n    {\n      \"domain\": \"Analytics\",\n      \"years_experience\": 8.2\n    },\n    {\n      \"domain\": \"Management\",\n      \"years_experience\": 8.2\n    },\n    {\n      \"domain\": \"Supply Chain\",\n      \"years_experience\": 4\n    },\n    {\n      \"domain\": \"Mining Engineering\",\n      \"years_experience\": 3.2\n    }\n  ],\n  \"education\": [\n    {\n      \"category\": \"University\",\n      \"degree_level\": \"Bachelor"s Degree\",\n      \"field_of_study\": \"Mining and Mineral Processing Engineering\"\n    }\n  ],\n  \"total_experience_years\": \"11.4\"\n}\n"
</candidate_profile>

<requirement_strings>
["Demonstrate strong ability to work with multiple stakeholders",
 "Minimum of 10 years-Relevant experience",
 "with at least 5 years in a leadership role",
 "Epic Healthy Planet or Compass Rose",
 "SQL",
 "Epic Clarity",
 "Caboodle"]
</requirement_strings>
"""},
    {"role": "assistant", "content": """\
{
  "assessed_objects": [
    {
      "requirement_string": "Demonstrate strong ability to work with multiple stakeholders",
      "match_reasoning": "Match found. The skill "Stakeholder Management" is listed in the candidate"s detailed_skills with 8.2 years of experience.",
      "match": true
    },
    {
      "requirement_string": "Minimum of 10 years-Relevant experience",
      "match_reasoning": "Match found. The candidate"s total_experience_years is 11.4, which meets the "10+" year requirement.",
      "match": true
    },
    {
      "requirement_string": "with at least 5 years in a leadership role",
      "match_reasoning": "Match found. Candidate has 8.2 years of "Leadership" experience listed in detailed_skills and 8.2 years of "Management" experience in domain_specific_experience, which meets the "5+" year requirement.",
      "match": true
    },
    {
      "requirement_string": "Epic Healthy Planet or Compass Rose",
      "match_reasoning": "No match. The required skill "Epic Healthy Planet or Compass Rose" is not mentioned in the candidate"s detailed_skills.",
      "match": false
    },
    {
      "requirement_string": "SQL",
      "match_reasoning": "Match found. The skill "SQL" is listed in the candidate"s detailed_skills with 7 years of experience.",
      "match": true
    },
    {
      "requirement_string": "Epic Clarity",
      "match_reasoning": "No match. The required skill "Epic Clarity" is not mentioned in the candidate"s detailed_skills.",
      "match": false
    },
    {
      "requirement_string": "Caboodle",
      "match_reasoning": "No match. The required skill "Caboodle" is not mentioned in the candidate"s detailed_skills.",
      "match": false
    }
  ]
}"""}
]