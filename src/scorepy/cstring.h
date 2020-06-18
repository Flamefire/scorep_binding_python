#pragma once

#include <cassert>
#include <cstring>

namespace scorepy
{

/// Thin wrapper around a C-String (NULL-terminated sequence of chars)
class CString
{
    const char* s_;

public:
    CString(const char* s) : s_(s)
    {
        assert(s_);
    }

    constexpr const char* c_str() const
    {
        return s_;
    }
    /// Find the first occurrence of the character and return a pointer to it or NULL if not found
    const char* find(char c) const
    {
        return std::strchr(s_, c);
    }
    template <size_t N>
    bool starts_with(const char (&prefix)[N]) const
    {
        return std::strncmp(s_, prefix, N - 1u) == 0;
    }

    friend bool operator==(const CString& lhs, const CString& rhs)
    {
        return std::strcmp(lhs.s_, rhs.s_) == 0;
    }
    friend bool operator!=(const CString& lhs, const CString& rhs)
    {
        return !(lhs == rhs);
    }
};

} // namespace scorepy
