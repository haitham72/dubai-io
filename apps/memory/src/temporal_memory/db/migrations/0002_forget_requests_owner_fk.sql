-- U1a could create this table before 0001, without its owner foreign key.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'forget_requests'::regclass
          AND confrelid = 'owners'::regclass
          AND contype = 'f'
          AND confdeltype = 'c'
          AND conkey = ARRAY[(
              SELECT attnum FROM pg_catalog.pg_attribute
              WHERE attrelid = 'forget_requests'::regclass AND attname = 'owner'
          )]
          AND confkey = ARRAY[(
              SELECT attnum FROM pg_catalog.pg_attribute
              WHERE attrelid = 'owners'::regclass AND attname = 'id'
          )]
    ) THEN
        LOCK TABLE owners, forget_requests IN SHARE ROW EXCLUSIVE MODE;
        DELETE FROM forget_requests AS receipt
        WHERE NOT EXISTS (SELECT 1 FROM owners WHERE owners.id = receipt.owner);

        ALTER TABLE forget_requests
            ADD CONSTRAINT fk_forget_requests_owner
            FOREIGN KEY (owner) REFERENCES owners(id) ON DELETE CASCADE;
    END IF;
END
$$;
