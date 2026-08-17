class IRepository:
    def get_all_raw_filenames(self):
        raise NotImplementedError

    def find_all(self):
        raise NotImplementedError

    def get_by_id(self, id):
        raise NotImplementedError

    def find_the_last_uploaded_file_date(self):
        raise NotImplementedError

    def save(self, filename, obj):
        raise NotImplementedError

    def save_parsed(self, filename, obj):
        raise NotImplementedError

    def delete_all(self):
        raise NotImplementedError

    def is_meta(self, filename):
        pass
