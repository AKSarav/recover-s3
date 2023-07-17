# script to recover S3 files by deleting the delete marker
# and restoring the file to the original location

import boto3
import sys
import argparse
import json
import threading
import time
import pdb

NextVersionIdMarker = None
NextKeyMarker = None
Repeat = True
Results={'Success': 0 ,'Failed' : 0 }
TotalFiles=[]
TotalDeleteMarkers=[]
RecoverableFiles=[] # Files with delete marker and source file present
NonRecoverableFiles=[] # Files with delete marker but source file missing
RecoverableFilesData=[] # Metadata of Recoverable Files

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

        return response
    else:
        print("INFO: No delete markers found for prefix '{}' in bucket '{}'".format(args.prefix,args.bucket))
        return []

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Recover S3 files by deleting the delete marker and restoring the file to the original location')
    parser.add_argument('--bucket', help='S3 bucket name', required=True)
    parser.add_argument('--prefix', help='S3 prefix', required=True)
    parser.add_argument('--region', help='S3 region', required=True)
    parser.add_argument('--dryrun', help='Recovery would not be done in dryrun', required=False, action='store_true')
    args = parser.parse_args()

    S3 = boto3.client('s3', region_name=args.region)
   
    # call listdeletedversion to get all delete markers

    iteration = 0
    while Repeat :
        print("\nINFO: Iteration: {}".format(iteration))
        response = listdeletedversion()
        if response == []:
            Repeat = False
            break
        else:
            TotalDeleteMarkers.extend(response['DeleteMarkers'])
            TotalFiles.extend(response['Versions'])
            delete_markers = response
            print("INFO: No of Delete markers found so far : {} in Iteration {}".format(len(TotalDeleteMarkers), iteration))
            print("INFO: Saving delete Markers...")
        iteration += 1

    

    print("\nINFO: Total Delete Markers found: {} for prefix {}".format(len(TotalDeleteMarkers),args.prefix))
    # Some files might have multiple versions, so the total files found might be more than the total delete markers found.
    print("INFO: Total Files found: {} for prefix {}".format(len(TotalFiles),args.prefix))
    
    
    # Parse through the Total Files and Collect the Keys
    TotalFilesKeys = []
    for file in TotalFiles:
        TotalFilesKeys.append(file['Key'])


    for delete_marker in TotalDeleteMarkers:
        ## 
        # check if source file is present for the delete marker key
        # sometimes, only delete marker is present for the key and the source file would be deleted 
        # in that case, we cannot recover the file
        # if source file is present, we can recover the file by deleting the delete marker
        ## 
        if str(delete_marker['Key']) in str(TotalFiles):
            # print("INFO: Source file found for Key {} with Version ID {} ".format(delete_marker['Key'],delete_marker['VersionId']))
            RecoverableFiles.append(delete_marker)
            
            # get the data from TotalFiles and add it to RecoverableFilesData using the map
            RecoverableFilesData.append(list(filter(lambda x: x['Key'] == delete_marker['Key'], TotalFiles))[0])
                        
        else:
            print("INFO: Source file not found for Key {} with Version ID {} ".format(delete_marker['Key'],delete_marker['VersionId']))
            NonRecoverableFiles.append(delete_marker)

    print("\nINFO: Total Recoverable Files: {}".format(len(RecoverableFiles)))
    print("INFO: Total Non-Recoverable Files: {}".format(len(NonRecoverableFiles)))

    # Save all the files as HTML table 
    
    with open('Report.html', 'w') as f:

        # add bootstrap to the html file to make it look good
        f.write('''
            <html>
            <head>
            <link rel='stylesheet' href='https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css'>
            <script src='https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js'></script>
            <script src='https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js'></script>
            <link rel='stylesheet' href='https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css'>
            <script src='https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js'></script>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Ubuntu&display=swap" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">
            <script type="text/javascript">
                    let table = new DataTable('#myTable', {
                        responsive: true
                    });
                    $(document).ready( function () {
                        $('#Summary').DataTable();
                        $('#Recover').DataTable(
                            {
                                autoWidth: false,
                                columns : [
                                    { width : '50%' },
                                    { width : '20%' },
                                    { width : '20%' },
                                    { width : '20%' },           
                                ] 
                            });
                        $('#NonRecover').DataTable({
                                autoWidth: false,
                                columns : [
                                    { width : '50%' },
                                    { width : '20%' },
                                    { width : '20%' },
                                    { width : '20%' },           
                                ] 
                            });
                        $('#Total').DataTable({
                                autoWidth: false,
                                columns : [
                                    { width : '50%' },
                                    { width : '20%' },
                                    { width : '20%' },
                                    { width : '20%' },           
                                ] 
                            });
                    } );
                </script>
                ''')
        f.write('''<style>
        table.dataTable tbody td {
            word-break: break-word;
            vertical-align: top;
        }
        body{
            background: rgb(240, 181, 223);
            background: linear-gradient(90deg, rgba(240, 181, 223, 1) 0%, rgba(138, 187, 226, 1) 100%);
            font-family: 'Open Sans', sans-serif;
        }

        .container {
            background-color: white;
            margin-top: 2% !important;
            margin-bottom: 2% !important;
            /* add shadow effect */
            /* -webkit-box-shadow: 0px 0px 20px 0px rgba(0, 0, 0, 0.75); */
            -moz-box-shadow: 0px 0px 20px 0px rgba(0, 0, 0, 0.75);
            box-shadow: 0px 0px 20px 0px rgba(0, 0, 0, 0.75);
        }

        h1{
            font-family: 'Ubuntu', sans-serif;
        }

        h2,
        h3 {
            color: black;
            font-family: 'Ubuntu', sans-serif;
            background-color: aliceblue;
            font-weight: 800;
            font-size: 24px;
            padding: 1%;
            margin-left: -2%;
        }

        .jumbotron {
            padding-top: 10px !important;
            padding-bottom: 10px !important;
            margin-bottom: 30px;
            color: inherit;
            background-color: aliceblue;
            margin-top: -5px;
            width: 60%;
            margin-left: -1%;
            float: left !important;
        }

        code {
            color: rgba(0, 0, 0, 0.37);
            background-color: transparent;
        }

        .info {
            margin-top: 2%;
            margin-left: 2%;
            margin-right: 2%;
            float: right;
        }
        .tagline{
            font-family: 'Ubuntu', sans-serif;
            font-size: 16px !important;
            color: rgba(0, 0, 0, 0.37) !important;
        }
        .footer{
            display: flex;
            padding: 2%;
            margin-bottom: -1%;
            margin-top: 3%;
            background-color: aliceblue;
            color: black;
        }
        .footer__right{
            margin-left: 30%;
        }
    </style>''')
        f.write("</head><body>")
        f.write('''
            <div class='container'>
            <!-- jumbotron -->
            <div class="row">
                <div class="col">
                    <div class='jumbotron' style="float: left">
                        <h1>Recover<span style="font-weight: bold;">S3</span></h1>
                        <p class="tagline">Recover deleted files from Versioned S3 bucket</p>
                    </div>
                </div>
                <div class="col info">
                        <p><img src='https://img.icons8.com/windows/42/github' />https://github.com/aksarav/recovers3.git</p>
                        <!-- website link with icon -->
                        <p><img src='https://img.icons8.com/windows/42/web'/>https://devopsjunction.com/recover-s3</p>
                </div>
            </div>
                ''')
        # add the summary table
        f.write("<h3>Recover S3 - Summary</h3></br>")
        f.write("<table id='Summary' class='display'><thead><th>Bucket</th><th>Prefix</th><th>Region</th><th>Recoverable Files</th><th>Non-Recoverable Files</th><th>Total Files</th><th>Total Delete Markers</th></thead>")
        f.write("<tbody><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tbody>".format(args.bucket,args.prefix,args.region,len(RecoverableFiles),len(NonRecoverableFiles),len(TotalFiles),len(TotalDeleteMarkers)))
        f.write("</table>")
        f.write("<br><br>")

        # add CSS to the html file to make it look good
        #f.write("<style>table, th, td {border: 1px solid black; border-collapse: collapse;} th, td {padding: 5px; text-align: left;}</style>")

        
        htmlfields="<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
        f.write("<h3>Recoverable Files</h3><br>")
        f.write("<table  id='Recover' class='display'><thead><th>Key</th><th>Version ID</th><th>Last Modified</th><th>Size</th></thead><tbody>")
        for file in RecoverableFilesData:
            f.write(htmlfields.format(file['Key'],file['VersionId'],file['LastModified'],file['Size']))
        f.write("</tbody></table>")

        f.write("<table  id='NonRecover' class='display'><thead><th>Key</th><th>Version ID</th></thead><tbody>")
        f.write("<h3>Non Recoverable Files</h3><br>")
        for file in NonRecoverableFiles:
            f.write(htmlfields.format(file['Key'],file['VersionId']))
        f.write("</tbody></table>")
    
        f.write("<table  id='Total' class='display'><thead><th>Key</th><th>Version ID</th><th>Last Modified</th><th>Size</th></thead><tbody>")
        f.write("<h3>Total Files</h3><br>")
        for file in TotalFiles:
            f.write(htmlfields.format(file['Key'],file['VersionId'],file['LastModified'],file['Size']))
        f.write("</tbody></table>")
        f.write('''
            <hr><footer>
                        <div class="footer">
                            <div class="footer__right">
                                <div class="footer__right__text">
                                    <p> For further reference visit <a href="https://github.com/AKSarav/recover-s3">https://github.com/AKSarav/recover-s3</a></p>
                                </div>
                            </div>
                        </div>
                    </footer>
                ''')
        f.write("</div></body></html>")
    

    
    # Process delete markers
    if not args.dryrun:
        input("\nPress Enter to start the recovery process...")
        print("INFO: Starting the recovery process...")
        for delete_marker in RecoverableFiles:
                #print("Starting thread for Key {} with Version ID {} ".format(delete_marker['Key'],delete_marker['VersionId']))
                r = recoverfiles(S3, args.bucket, delete_marker['Key'], delete_marker['VersionId'])
                threading.Thread(target=r.run).start()
                while threading.active_count() > 10:
                    # sleep for a while until a thread is available
                    print("Waiting for a threads to finish")
                    time.sleep(1)
    else:
        print("INFO: Dry run enabled. Recovery process will not start")
        sys.exit(0)

    # wait for all threads to finish
    while threading.active_count() > 1:
        # sleep for a while until a thread is available
        time.sleep(1)
        print("Waiting for all threads to finish")

    print("INFO: All delete markers removed for prefix '{}' in bucket '{}'".format(args.prefix,args.bucket))
    print("INFO: Total Success: {} and Failed: {}".format(Results['Success'],Results['Failed']))
    sys.exit(0)