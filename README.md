## Recover S3

This script will recover files from S3 that have been deleted by
removing the `deletemarker` from the S3 object.

This is useful when you have a bucket with versioning enabled and you have deleted a file by mistake.

As of now, this script will only recover the files that have been deleted and not the files that have been overwritten.

Also, this script will not recover the files that have been deleted and overwritten by another file.

we have added threading to speed up the process. As part of benchmarking, we have recovered 10000 files in 8 minutes.

The speed of the script depends on the number of files that you are trying to recover, the network speed and the file size.


### Pre-requisites

* Python 3
* Boto3
* pip
* AWS Access Key and Secret Key
* Permissions to access S3 bucket and list and delete objects


### Installation

Clone the repository and install the dependencies.

```
$ git clone https://github.com/AKSarav/recover-s3.git
$ pip install -r requirements.txt
```


&nbsp;
#### Usage

```
python recover-s3-files.py [-h] --bucket BUCKET --prefix PREFIX --region

optional arguments:
  -h, --help       show this help message and exit
  --bucket BUCKET  S3 bucket name
  --prefix PREFIX  S3 prefix
  --region REGION  S3 region
```
&nbsp;

#### Example

```
python recover-s3-files.py --bucket my-bucket --prefix my-prefix --region us-east-1
```
&nbsp;

#### Author
Sarav Thangaraj - [linkedin](https://linkedin.com/in/aksarav) | [Blog](https://devopsjunction.com)

&nbsp;
    
#### License
MIT
