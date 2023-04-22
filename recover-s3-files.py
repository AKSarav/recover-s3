# script to recover S3 files by deleting the delete marker
# and restoring the file to the original location

import boto3
import sys
import argparse
import json
import threading
import time


NextVersionIdMarker = None
NextKeyMarker = None
Repeat = True
Results={'Success': 0 ,'Failed' : 0 }


class recoverfiles(threading.Thread):
    def __init__(self, S3obj, bucket, Key, VersionId):
        threading.Thread.__init__(self)
        self.Key = Key
        self.VersionId = VersionId
        self.S3 = S3obj
        self.bucket = bucket

    def run(self):
        print("Deleting delete marker for Key {} with Version ID {} ".format(self.Key,self.VersionId))
        response = self.S3.delete_object(
            Bucket=self.bucket,
            Key=self.Key,
            VersionId=self.VersionId
        )
        #print("Response: " + json.dumps(response))

        if response['ResponseMetadata']['HTTPStatusCode'] == 204:
            print("INFO: Delete Marker removed for Key {} with Version ID {} ".format(self.Key,self.VersionId))
            Results['Success'] += 1
        else:
            print("ERROR: Delete Marker not removed for Key {} with Version ID {} ".format(self.Key,self.VersionId))
            Results['Failed'] += 1

def listdeletedversion():
    # get all delete markers for the prefix with recursive
    global NextVersionIdMarker, NextKeyMarker, Repeat

    if NextVersionIdMarker is None or NextKeyMarker is None:
        response = S3.list_object_versions(
            Bucket=args.bucket,
            Prefix=args.prefix,
            MaxKeys=1000,
        )
    else:
        response = S3.list_object_versions(
            Bucket=args.bucket,
            Prefix=args.prefix,
            MaxKeys=1000,
            VersionIdMarker=NextVersionIdMarker,
            KeyMarker=NextKeyMarker
        )

    if 'DeleteMarkers' in response:
        if 'NextVersionIdMarker' in response and 'NextKeyMarker' in response:
            NextVersionIdMarker = response['NextVersionIdMarker']
            NextKeyMarker = response['NextKeyMarker']
            Repeat = True
        else:
            Repeat = False

        for delete_marker in response['DeleteMarkers']:
            print("INFO: Delete Marker found for Key {} with Version ID {} ".format(delete_marker['Key'],delete_marker['VersionId']))

        return response['DeleteMarkers']
    else:
        print("INFO: No delete markers found for prefix '{}' in bucket '{}'".format(args.prefix,args.bucket))
        return []

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Recover S3 files by deleting the delete marker and restoring the file to the original location')
    parser.add_argument('--bucket', help='S3 bucket name', required=True)
    parser.add_argument('--prefix', help='S3 prefix', required=True)
    parser.add_argument('--region', help='S3 region', required=True)
    args = parser.parse_args()

    S3 = boto3.client('s3', region_name=args.region)
   
    # call listdeletedversion to get all delete markers

    while Repeat :
        response = listdeletedversion()
        if response == []:
            Repeat = False
            break
        else:
            delete_markers = response
            for delete_marker in delete_markers:
                print("Starting thread for Key {} with Version ID {} ".format(delete_marker['Key'],delete_marker['VersionId']))
                r = recoverfiles(S3, args.bucket, delete_marker['Key'], delete_marker['VersionId'])
                threading.Thread(target=r.run).start()
                while threading.active_count() > 10:
                    # sleep for a while until a thread is available
                    print("Waiting for a threads to finish")
                    time.sleep(1)


    # wait for all threads to finish
    while threading.active_count() > 1:
        # sleep for a while until a thread is available
        time.sleep(1)
        print("Waiting for all threads to finish")

    print("INFO: All delete markers removed for prefix '{}' in bucket '{}'".format(args.prefix,args.bucket))

    print("INFO: Total Success: {} and Failed: {}".format(Results['Success'],Results['Failed']))
    sys.exit(0)