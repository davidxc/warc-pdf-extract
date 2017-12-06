create table token_doi(title_token char(64) not null, doi text not null, title text not null, authors text not null);
create unique index token_doi_doi on token_doi (doi);
create index token_doi_tile_token on token_doi (title_token);
