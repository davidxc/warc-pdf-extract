create table token_doi(token_title char(64) not null, doi text not null, title text not null, authors text not null);
create unique index token_doi_doi on token_doi (doi);
create index token_doi_ttile on token_doi (token_title);
.mode tabs
.import tokenized_crossref.tsv files_id_doi
