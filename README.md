# Alexa skills - When's my next bin collection?
## Where to get
https://www.amazon.co.uk/dp/B0BTD6LS61/

## How to use
### Ask
> Alexa, ask next bin collection.
 
or

> Alexa, ask bin collection.

### Reply
> Recycling bin will be collected Monday, 2023-01-02

---

## How to update the bin collection calendar
### Understand the persistent storage
A DynamoDB table in the Alexa hosted environment

* Partition key: `id`
  * Description: Week start date
  * Example: 2023-01-02
* Attribute: `bin_type`
  * Description: Bin type
  * Example: Recycling bin
* Attribute: `collection_date`
  * Example: 2023-01-03

### Prepare and upload the CSV file
| id | bin_type | collection_date |
|-|-|-|
|xxx|xxx|xxx|
|xxx|xxx|xxx|
|xxx|xxx|xxx|

* Refer to the [sample](calendars/main.csv)
* Save as file name `main.csv`
* Upload to the S3 bucket: `s3://<bucket-name>/inbox/`
* Invoke the skills once
