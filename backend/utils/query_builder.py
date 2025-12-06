"""
Query builder utility for constructing dynamic SQL queries
"""


class QueryBuilder:
    """Helper class for building dynamic SQL queries safely"""

    # Valid SQL operators
    VALID_OPERATORS = {
        '=': '=',
        '!=': '!=',
        '<>': '<>',
        '>': '>',
        '<': '<',
        '>=': '>=',
        '<=': '<=',
        'LIKE': 'LIKE',
        'ILIKE': 'ILIKE',
        'IN': 'IN',
        'NOT IN': 'NOT IN',
        'IS NULL': 'IS NULL',
        'IS NOT NULL': 'IS NOT NULL',
        'BETWEEN': 'BETWEEN'
    }

    @staticmethod
    def validate_operator(operator):
        """
        Validate that the operator is safe to use

        Args:
            operator: SQL operator string

        Returns:
            Validated operator or raises ValueError
        """
        op = operator.strip().upper()
        if op not in QueryBuilder.VALID_OPERATORS:
            raise ValueError(f"Invalid operator: {operator}")
        return QueryBuilder.VALID_OPERATORS[op]

    @staticmethod
    def build_where_clause(field, operator, value):
        """
        Build a WHERE clause safely

        Args:
            field: Column name
            operator: SQL operator
            value: Comparison value

        Returns:
            Tuple of (where_clause_string, parameters_dict)
        """
        validated_op = QueryBuilder.validate_operator(operator)

        # Handle different operator types
        if validated_op in ['IS NULL', 'IS NOT NULL']:
            return f"{field} {validated_op}", {}

        elif validated_op in ['LIKE', 'ILIKE']:
            return f"{field} {validated_op} :value", {'value': f"%{value}%"}

        elif validated_op == 'BETWEEN':
            # Expect value to be a tuple/list of (min, max)
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError("BETWEEN requires a list/tuple of two values")
            return f"{field} BETWEEN :value_min AND :value_max", {
                'value_min': value[0],
                'value_max': value[1]
            }

        elif validated_op in ['IN', 'NOT IN']:
            # Handle IN operator with list of values
            if not isinstance(value, (list, tuple)):
                value = [value]
            placeholders = ','.join([f':value_{i}' for i in range(len(value))])
            params = {f'value_{i}': v for i, v in enumerate(value)}
            return f"{field} {validated_op} ({placeholders})", params

        else:
            # Standard comparison operators
            return f"{field} {validated_op} :value", {'value': value}

    @staticmethod
    def build_multi_filter(filters, logic='AND'):
        """
        Build WHERE clause for multiple filters

        Args:
            filters: List of filter dictionaries with 'field', 'operator', 'value'
            logic: Logical operator to combine filters ('AND' or 'OR')

        Returns:
            Tuple of (where_clause_string, parameters_dict)
        """
        if logic.upper() not in ['AND', 'OR']:
            raise ValueError("Logic must be 'AND' or 'OR'")

        clauses = []
        all_params = {}

        for i, filter_item in enumerate(filters):
            field = filter_item['field']
            operator = filter_item['operator']
            value = filter_item['value']

            clause, params = QueryBuilder.build_where_clause(field, operator, value)

            # Rename parameters to avoid conflicts
            renamed_params = {f"{k}_{i}": v for k, v in params.items()}
            renamed_clause = clause
            for old_key, new_key in zip(params.keys(), renamed_params.keys()):
                renamed_clause = renamed_clause.replace(f":{old_key}", f":{new_key}")

            clauses.append(f"({renamed_clause})")
            all_params.update(renamed_params)

        where_clause = f" {logic.upper()} ".join(clauses)
        return where_clause, all_params

    @staticmethod
    def sanitize_field_name(field_name):
        """
        Sanitize field name to prevent SQL injection

        Args:
            field_name: Column name to sanitize

        Returns:
            Sanitized field name
        """
        # Only allow alphanumeric characters and underscores
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field_name):
            raise ValueError(f"Invalid field name: {field_name}")
        return field_name
