
BASE_DIR="/data/pdfs/identified/"
PDF_DIR="$BASE_DIR/pdf/"
THIS_RUN="run`date '+%s'`"
GROBID_JAR="/home/bnewbold/src/grobid/grobid-grobid-parent-0.4.4/grobid-core/target/grobid-core-0.4.4-SNAPSHOT.one-jar.jar"
CERMINE_JAR="/home/bnewbold/tmp/cermine-impl-1.13-jar-with-dependencies.jar"
SCIENCEPARSE_JAR="/home/bnewbold/src/science-parse/cli/target/scala-2.11/science-parse-cli-assembly-1.3.0.jar"

echo "### GROBID"
mkdir -p $BASE_DIR/grobid
rm -f $BASE_DIR/grobid/*
/usr/bin/time -v -o grobid_timing.$THIS_RUN.txt java -Xmx6G -jar $GROBID_JAR -gH /home/bnewbold/src/grobid/grobid-grobid-parent-0.4.4/grobid-home/ -dIn $PDF_DIR -dOut $BASE_DIR/grobid -r -exe processHeader

echo "### CERMINE"
mkdir -p $BASE_DIR/cermine
rm -f $BASE_DIR/cermine/*
/usr/bin/time -v -o cermine_timing.$THIS_RUN.txt java -Xmx6g -cp $CERMINE_JAR pl.edu.icm.cermine.ContentExtractor -path $PDF_DIR -outputs jats

echo "### Science Parse"
mkdir -p $BASE_DIR/scienceparse
rm -f $BASE_DIR/scienceparse/*
/usr/bin/time -v -o scienceparse_timing.$THIS_RUN.txt java -Xmx6g -jar $SCIENCEPARSE_JAR $PDF_DIR -o $BASE_DIR/scienceparse
