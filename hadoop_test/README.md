
Plan:
- input: CDX file with 100k PDF URLs
- python script fetches from wayback, pushes to GROBID, outputs status
- configure ~50 workers to start



## Commands

Grab and re-upload sample set:

    gohdfs head -n 100001 pdfs/gobal-20170412234601-pdfs-prefixed/part-00000 | cut -f2- -d' ' | tail -n+2 > 100k_random_gwb_pdf.cdx
    gohdfs put 100k_random_gwb_pdf.cdx 100k_random_gwb_pdf.cdx

From the cluster:

    $HADOOP_HOME/bin/hadoop jar $HADOOP_HOME/../hadoop-mapreduce/hadoop-streaming.jar \
        -D mapred.job.queue.name=extraction \
        -D mapreduce.input.lineinputformat.linespermap=1000 \
        -D mapred.map.tasks=50 \
        -D mapred.reduce.tasks=0 \
        -inputformat org.apache.hadoop.mapred.lib.NLineInputFormat \
        -input '/user/bnewbold/100k_random_gwb_pdf.cdx' \
        -output '/user/bnewbold/grobid_test000.out' \
        -mapper 'grobid_load.py' \
        -file grobid_load.py
